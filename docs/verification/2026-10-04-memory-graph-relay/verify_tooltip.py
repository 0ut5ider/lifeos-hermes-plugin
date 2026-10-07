# ABOUTME: Executes the actual native graph tooltip function in a real Chromium DOM.
# ABOUTME: Records formatting controls and refuses executable title or category markup.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from playwright.sync_api import sync_playwright


def main():
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    text = source.read_text()
    start = text.index('    function showTooltip(')
    end = text.index('    function hideTooltip(', start)
    constants = text[text.index('const CATEGORY_COLORS:'):text.index('interface SimNode')]
    function = text[start:end]
    compiled = subprocess.run(['bun', '-e',
        'const source=await Bun.stdin.text();process.stdout.write(new Bun.Transpiler({loader:"ts"}).transformSync(source));'],
        input=constants + '\n' + function, text=True, capture_output=True, check=True)
    assert compiled.stderr == '', compiled.stderr
    expression = '''async (node) => {
      window.__graphTooltipProbe = 0;
      document.body.replaceChildren();
      const tooltipEl = document.createElement('div');
      document.body.appendChild(tooltipEl);
      const stateRef = {current: {focused: 'synthetic-focused'}};
      const colorMapRef = {current: {research: '#abcdef'}};
      ''' + compiled.stdout + '''
      showTooltip(node, 10, 20);
      await new Promise(resolve => setTimeout(resolve, 40));
      return {text: tooltipEl.textContent, html: tooltipEl.innerHTML,
        markup: tooltipEl.querySelectorAll('svg,img,b,em').length,
        executed: window.__graphTooltipProbe,
        children: [...tooltipEl.children].map(child => ({text: child.textContent, color: child.style.color})),
        position: {left: tooltipEl.style.left, top: tooltipEl.style.top, opacity: tooltipEl.style.opacity}};
    }'''
    cases = [
        {'name': 'native-format', 'node': {'id': 'synthetic-focused', 'title': 'Synthetic plain title',
            'category': 'research', 'backlinkCount': 3}},
        {'name': 'literal-title', 'node': {'id': 'synthetic-other', 'title': 'Synthetic <b>literal & title</b>',
            'category': 'research', 'backlinkCount': 0}},
        {'name': 'executable-title', 'node': {'id': 'synthetic-other',
            'title': 'Synthetic <svg onload="window.__graphTooltipProbe=1"></svg>',
            'category': 'research', 'backlinkCount': 0}},
        {'name': 'literal-category', 'node': {'id': 'synthetic-other', 'title': 'Synthetic category title',
            'category': '<em>synthetic-category</em>', 'backlinkCount': 0}},
    ]
    outcomes = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        for case in cases:
            outcomes.append({**case, 'actual': page.evaluate(expression, case['node'])})
        version = browser.version
        browser.close()
    destination.write_text(json.dumps({'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'browser': version, 'outcomes': outcomes, 'page_errors': errors}, indent=2) + '\n')
    assert errors == [], errors
    control = outcomes[0]['actual']
    assert control['position'] == {'left': '22px', 'top': '8px', 'opacity': '1'}, control
    assert [child['text'] for child in control['children']] == [
        'RESEARCH', 'Synthetic plain title', '3 backlinks', 'click again to open'], control
    assert control['children'][0]['color'] == 'rgb(171, 205, 239)', control
    for outcome in outcomes:
        actual, node = outcome['actual'], outcome['node']
        assert actual['markup'] == 0 and actual['executed'] == 0, outcome
        assert actual['children'][1]['text'] == node['title'], outcome
        assert actual['children'][0]['text'] == node['category'].replace('-', ' ', 1).upper(), outcome
    print(f"Four native tooltip cases pass in Chromium {version}")


if __name__ == '__main__':
    main()
