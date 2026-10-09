# ABOUTME: Projects retained conversation content without removed native claims.
# ABOUTME: Preserves protocol identifiers and leaves persisted transcripts unchanged.
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import hashlib
import sys
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


def user_proof(content):
    if isinstance(content,str):
        return {'kind':'text','length':len(content),'digest':hashlib.sha256(content.encode()).hexdigest()}
    if isinstance(content,list):
        serialized = json.dumps(content,sort_keys=True,separators=(',',':'))
        return {'kind':'blocks','length':len(content),'digest':hashlib.sha256(serialized.encode()).hexdigest()}
    if content is None:
        return None
    raise ValueError('Memory admission requires materialized user input')


def user_parts(content,proof):
    length = proof.get('length')
    if type(length) is not int or length < 0:
        raise ValueError('Memory history requires a valid user input proof')
    if proof.get('kind')=='text' and isinstance(content,str):
        original,suffix = content[:length],content[length:]
    elif proof.get('kind')=='blocks' and isinstance(content,list):
        original,suffix = content[:length],content[length:]
    else:
        raise ValueError('Memory history cannot identify the current user input')
    if user_proof(original) != proof:
        raise ValueError('Memory history cannot verify the current user input')
    return original,suffix


def _generated_user(message):
    # The active Hermes loop owns this classifier, including crash-restored nudges.
    module = sys.modules.get('agent.context_compressor')
    compressor = getattr(module, 'ContextCompressor', None)
    if compressor is None:
        return False
    return (module._content_text_for_contains(message.get('content')).strip() == REMOVED
        or compressor._is_synthetic_compression_user_turn(message))


def _current_user(messages, user_input):
    users = [(index, message) for index, message in enumerate(messages) if message.get('role') == 'user']
    for index, message in reversed(users):
        if user_input is not None:
            try:
                user_parts(message.get('content'), user_input)
            except ValueError:
                if not _generated_user(message):
                    raise
            else:
                return index
        elif not _generated_user(message):
            return index
    if user_input is not None and users:
        raise ValueError('Memory history cannot verify the current user input')
    return -1


def retained_messages(messages,user_input=None):
    current_user = _current_user(messages, user_input)
    retained = [(index,message) for index,message in enumerate(messages) if index != current_user]
    if current_user >= 0 and user_input is not None:
        message = messages[current_user]
        _,suffix = user_parts(message.get('content'),user_input)
        retained.append((current_user,{**message,'content':suffix}))
    return retained


def project_request(request: dict[str,Any], excluded: Callable[[str],bool], user_input=None) -> dict[str,Any]:
    field = 'messages' if 'messages' in request else 'input'
    messages = request.get(field)
    if not isinstance(messages,(list,tuple)) or any(not isinstance(message,Mapping) for message in messages):
        label = 'chat messages' if field == 'messages' else 'Responses input'
        raise ValueError(f'Memory history repair requires materialized {label}')
    projected = deepcopy(list(messages))
    for index,derived in retained_messages(projected,user_input):
        message = projected[index]
        if message.get('role') in ('system','developer'):
            continue
        for key in ('content','reasoning','reasoning_content','arguments','output','summary'):
            if key in derived:
                value = project_value(derived[key],excluded)
                if key == 'content' and derived is not message:
                    original,_ = user_parts(message[key],user_input)
                    value = original+value
                message[key] = value
        for call in message.get('tool_calls') or []:
            if isinstance(call,dict) and isinstance(call.get('function'),dict):
                function = call['function']
                if 'arguments' in function:
                    function['arguments'] = project_value(function['arguments'],excluded)
    return {**request,field:projected}
