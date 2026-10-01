# ABOUTME: Projects retained conversation content without removed native claims.
# ABOUTME: Preserves protocol identifiers and leaves persisted transcripts unchanged.
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
from typing import Any, Callable


REMOVED = '[Content excluded after a memory correction or forget request.]'


def project_value(value: Any, excluded: Callable[[str], bool], depth: int = 0) -> Any:
    if depth > 32:
        raise ValueError('Memory history requires bounded materialized content')
    if isinstance(value,str):
        try:
            decoded = json.loads(value)
        except RecursionError as error:
            raise ValueError('Memory history requires bounded materialized content') from error
        except ValueError:
            return REMOVED if excluded(value) else value
        projected = project_value(decoded,excluded,depth+1)
        return json.dumps(projected) if projected != decoded else value
    if isinstance(value,Mapping):
        if any(not isinstance(key,str) or excluded(key) for key in value):
            raise ValueError('Memory history cannot rewrite protocol or content field names')
        return {key:project_value(item,excluded,depth+1) for key,item in value.items()}
    if isinstance(value,(list,tuple)):
        return [project_value(item,excluded,depth+1) for item in value]
    if value is None or isinstance(value,(bool,int,float)):
        return value
    raise ValueError('Memory history requires materialized content')


def retained_messages(messages):
    current_user = max((index for index,message in enumerate(messages) if message.get('role')=='user'),default=-1)
    return [(index,message) for index,message in enumerate(messages) if index != current_user]


def project_request(request: dict[str,Any], excluded: Callable[[str],bool]) -> dict[str,Any]:
    messages = request.get('messages')
    if not isinstance(messages,(list,tuple)) or any(not isinstance(message,Mapping) for message in messages):
        raise ValueError('Memory history repair requires materialized chat messages')
    projected = deepcopy(list(messages))
    for index,message in retained_messages(projected):
        if message.get('role') in ('system','developer'):
            continue
        for key in ('content','reasoning','reasoning_content'):
            if key in message:
                message[key] = project_value(message[key],excluded)
        for call in message.get('tool_calls') or []:
            if isinstance(call,dict) and isinstance(call.get('function'),dict):
                function = call['function']
                if 'arguments' in function:
                    function['arguments'] = project_value(function['arguments'],excluded)
    return {**request,'messages':projected}
