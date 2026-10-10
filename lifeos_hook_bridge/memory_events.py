# ABOUTME: Appends native event records through current owner authority and recoverable publication.
# ABOUTME: Serializes event writers on the memory transaction lock and retains bounded event history.
from datetime import datetime,timezone
import json
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_adoption import _owner
from .memory_knowledge_conformance import EVENTS,EVENT_LIMIT,_destination
from .memory_sources import authorize,CORPUS_LIMIT
from .memory_transaction import publish


def publication_paths(memory,scope,payload):
    if not _owner(scope) or payload['destination']!=EVENTS:
        raise MemoryUnavailable('Event appends require unrestricted owner publication authority')
    _destination(memory)
    return [EVENTS]


def append(memory,scope,*,path,event,request_id,source_session='',check_current=None):
    authorize(scope)
    if (not _owner(scope) or not isinstance(path,str) or not isinstance(event,dict)
            or any(not isinstance(event.get(key),str) or not 1<=len(event[key])<=256 for key in ('type','source'))
            or len(json.dumps(event,allow_nan=False).encode())>CORPUS_LIMIT):
        raise MemoryUnavailable('Native event append requires owner grants and bounded event fields')
    if not Path(path).is_absolute() or Path(path)!=memory.root/EVENTS:
        raise MemoryUnavailable('Native event appends require their declared installed destination')
    if check_current is not None:check_current()
    def apply(connection):
        destination=_destination(memory)
        timestamp=datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
        if memory._filter_history(connection,scope,json.dumps(event),timestamp)['excluded']:
            raise MemoryUnavailable('Native event append contains an excluded source label')
        before=destination.read_bytes() if destination.exists() else b''
        record={**event,'timestamp':timestamp,'session_id':source_session}
        content=before+(json.dumps(record,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
        if len(content)>EVENT_LIMIT:raise MemoryUnavailable('The native event history exceeds its publication limit')
        if check_current is not None:check_current()
        publish(destination,content)
        return {'status':'committed'}
    receipt=memory._operation(scope,request_id,{'operation':'event_append','destination':EVENTS,
        'event':event,'source_session':source_session},apply)
    if check_current is not None:check_current()
    return {'ok':receipt['status']=='committed','receipt':receipt}
