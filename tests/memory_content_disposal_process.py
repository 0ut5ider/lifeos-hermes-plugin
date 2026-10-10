# ABOUTME: Interrupts actual owner Content disposal after native publication or file movement.
# ABOUTME: Leaves committed or unknown receipts for the parent to verify exact file recovery.
import os
from pathlib import Path
import sys
from lifeos_hook_bridge.memory_access import NativeMemory
from lifeos_hook_bridge.memory_preferences import MemoryPreferences
from lifeos_hook_bridge import memory_moves

configuration,root,phase=sys.argv[1:]
original_move=memory_moves.move
count=0

def interrupt_move(source,destination):
    global count
    original_move(source,destination)
    count+=1
    if phase==str(count):os._exit(73)

memory_moves.move=interrupt_move
original_native=NativeMemory._native

def interrupt_native(memory,action,**values):
    result=original_native(memory,action,**values)
    if phase=='append' and action=='content_delete_append':os._exit(73)
    return result

NativeMemory._native=interrupt_native
if phase=='partial':
    def interrupt_cleanup(path):
        (path/'transcript.md').unlink()
        os._exit(73)
    memory_moves.shutil.rmtree=interrupt_cleanup
if phase=='committed':
    def interrupt_finish(moves,entries):os._exit(73)
    memory_moves.MemoryMoves.finish=interrupt_finish
preferences=MemoryPreferences(Path(configuration),Path(root),Path(sys.executable),
    Path(__file__).parents[1]/'lifeos_hook_bridge/memory_mcp.py')
preferences.content_action_response('/api/content/synthetic0',{'method':'DELETE'},
    account='dashboard:basic:synthetic-owner')
raise RuntimeError('The selected Content disposal does not interrupt')
