# ABOUTME: Verifies actual native search output before a model turn can satisfy memory acceptance.
# ABOUTME: Exports only matched references and refuses missing or unsuccessful tool results.
import json
import re


def verified_search(events, expected):
    refused={'verified':False,'references':[]}
    calls=[event for event in events if event.get('type')=='tool_use']
    results=[event for event in events if event.get('type')=='tool_result']
    if (len(calls)!=1 or calls[0].get('name')!='lifeos_memory_search' or len(results)!=1
            or results[0].get('name')!='lifeos_memory_search' or results[0].get('is_error') is not False):
        return refused
    try:
        output=json.loads(results[0]['output'])
    except (KeyError,ValueError,TypeError):
        return refused
    if not isinstance(output,dict) or output.get('status')!='ok' or not isinstance(output.get('results'),list):
        return refused
    references=[]
    for item in output['results']:
        if not isinstance(item,dict) or not isinstance(item.get('content'),str) or expected not in item['content']:
            continue
        reference=item.get('reference')
        if (not isinstance(reference,dict) or set(reference)!={'id','revision'}
                or not isinstance(reference['id'],str) or re.fullmatch('[0-9a-f]{32}',reference['id']) is None
                or type(reference['revision']) is not int or reference['revision']<1):
            continue
        references.append(reference)
    return {'verified':bool(references),'references':references}
