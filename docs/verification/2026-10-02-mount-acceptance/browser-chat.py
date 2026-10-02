# ABOUTME: Sends a synthetic acceptance prompt through the actual browser terminal.
# ABOUTME: Requires a private model reply and records the terminal outside the repository.
import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
cache=Path('/home/outsider/.cache/lifeos-plugin-memory/mount-acceptance-transfer-20261002')
out=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-02-mount-acceptance')
login=json.loads((cache/'browser-login.json').read_text())
frames=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 ctx=browser.new_context(viewport={'width':1600,'height':1100},permissions=['clipboard-read','clipboard-write'])
 page=ctx.new_page()
 page.goto('http://192.168.8.212:8921/login')
 page.locator('input[name="username"]').fill(login['username'])
 page.locator('input[name="password"]').fill(login['password'])
 page.get_by_role('button',name='Sign in',exact=True).click()
 page.wait_for_url('http://192.168.8.212:8921/')
 page.goto('http://192.168.8.212:8921/chat')
 page.wait_for_timeout(3000)
 page.get_by_role('button',name='New chat',exact=True).click()
 page.wait_for_timeout(7000)
 page.screenshot(path=str(out/'acceptance-chat-start.png'),full_page=True)
 terminal=page.locator('textarea[aria-label="Terminal input"]')
 terminal.focus()
 page.keyboard.insert_text('Reply with BROWSER-212-READY and name the system that provides your LifeOS context. Do not call any tools.')
 page.keyboard.press('Enter')
 deadline=time.monotonic()+180
 messages=[]
 while time.monotonic()<deadline:
  page.wait_for_timeout(2000)
  response=page.request.get('http://192.168.8.212:8921/api/sessions')
  sessions=response.json()
  for session in sessions.get('sessions',[]):
   if session['started_at'] < time.time()-240: continue
   record=page.request.get('http://192.168.8.212:8921/api/sessions/'+session['id']+'/messages?limit=500&order=latest').json()
   messages=record.get('messages',[])
   if any(m.get('role')=='assistant' and 'BROWSER-212-READY' in str(m.get('content')) for m in messages): break
  else: continue
  break
 page.screenshot(path=str(out/'acceptance-chat-reply.png'),full_page=True)
 success=any(m.get('role')=='assistant' and 'BROWSER-212-READY' in str(m.get('content')) for m in messages)
 (out/'browser-chat-result.json').write_text(json.dumps({'assistant_reply_verified':success,'messages':messages},indent=2)+'\n')
 print(json.dumps({'assistant_reply_verified':success}))
 assert success, 'No persisted assistant reply after the browser prompt'
 browser.close()
