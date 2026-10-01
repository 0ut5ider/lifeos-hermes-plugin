     1	# ABOUTME: Journals native file publication so interrupted memory operations can recover.
     2	# ABOUTME: Serializes cooperating writers and keeps temporary recovery copies private.
     3	
     4	from contextlib import contextmanager
     5	from contextvars import ContextVar
     6	import base64
     7	import fcntl
     8	import json
     9	import os
    10	from pathlib import Path
    11	import tempfile
    12	
    13	
    14	def publish(path: Path, data: bytes) -> None:
    15	    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    16	    descriptor, name = tempfile.mkstemp(prefix=".memory-", dir=path.parent)
    17	    temporary = Path(name)
    18	    try:
    19	        with os.fdopen(descriptor, "wb") as stream:
    20	            stream.write(data)
    21	            stream.flush()
    22	            os.fsync(stream.fileno())
    23	        os.replace(temporary, path)
    24	        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    25	        try:
    26	            os.fsync(descriptor)
    27	        finally:
    28	            os.close(descriptor)
    29	    finally:
    30	        temporary.unlink(missing_ok=True)
    31	
    32	
    33	class MemoryTransaction:
    34	    def __init__(self, state: Path, resolve):
    35	        self.state = state
    36	        self.resolve = resolve
    37	        self.journal = state / "memory-operation.json"
    38	        self._descriptor = ContextVar("memory_lock_descriptor", default=None)
    39	
    40	    @contextmanager
    41	    def lock(self):
    42	        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
    43	        descriptor = os.open(self.state / "memory-access.lock", os.O_CREAT | os.O_RDWR, 0o600)
    44	        token = self._descriptor.set(descriptor)
    45	        try:
    46	            fcntl.flock(descriptor, fcntl.LOCK_EX)
    47	            yield
    48	        finally:
    49	            self._descriptor.reset(token)
    50	            os.close(descriptor)
    51	
    52	    def inherited_descriptors(self) -> tuple[int, ...]:
    53	        descriptor = self._descriptor.get()
    54	        return () if descriptor is None else (descriptor,)
    55	
    56	    def flush_publication(self) -> None:
    57	        if not self.journal.exists():
    58	            return
    59	        for copy in json.loads(self.journal.read_text())["copies"]:
    60	            path = self.resolve(copy["path"])
    61	            if path.exists():
    62	                descriptor = os.open(path, os.O_RDONLY)
    63	                try:
    64	                    os.fsync(descriptor)
    65	                finally:
    66	                    os.close(descriptor)
    67	            if path.parent.exists():
    68	                descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    69	                try:
    70	                    os.fsync(descriptor)
    71	                finally:
    72	                    os.close(descriptor)
    73	
    74	    def prepare(self, writer: str, request_id: str, paths: list[str]) -> None:
    75	        copies = []
    76	        for name in sorted(set(paths)):
    77	            path = self.resolve(name)
    78	            copies.append({"path": name, "data": base64.b64encode(path.read_bytes()).decode() if path.exists() else None})
    79	        publish(self.journal, json.dumps({"writer": writer, "request_id": request_id, "copies": copies}).encode())
    80	
    81	    def recover(self, connection) -> None:
    82	        if not self.journal.exists():
    83	            return
    84	        operation = json.loads(self.journal.read_text())
    85	        row = connection.execute("SELECT receipt FROM operations WHERE writer=? AND request_id=?",
    86	                                 (operation["writer"], operation["request_id"])).fetchone()
    87	        if row is not None and json.loads(row["receipt"])["status"] != "unknown":
    88	            self.journal.unlink()
    89	            return
    90	        for copy in operation["copies"]:
    91	            path = self.resolve(copy["path"])
    92	            if copy["data"] is None:
    93	                path.unlink(missing_ok=True)
    94	            else:
    95	                publish(path, base64.b64decode(copy["data"], validate=True))
    96	        connection.execute("DELETE FROM operations WHERE writer=? AND request_id=?",
    97	                           (operation["writer"], operation["request_id"]))
    98	        connection.commit()
    99	        self.journal.unlink()
   100	
   101	    def finish(self) -> None:
   102	        self.journal.unlink(missing_ok=True)
