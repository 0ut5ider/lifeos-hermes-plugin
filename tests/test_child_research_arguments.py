# ABOUTME: Checks the native child research command contract without creating a model response.
# ABOUTME: Preserves tool-free JSON requests and refuses capabilities outside the declared web tools.
import argparse
import unittest
from lifeos_hook_bridge.bin.claude_direct import configure_arguments, _validate_arguments


class ChildResearchArgumentTests(unittest.TestCase):
    def arguments(self, *, output='json', tools='', allowed=''):
        parser = argparse.ArgumentParser()
        configure_arguments(parser)
        return parser.parse_args(['--print', '--model', 'synthetic-model', '--output-format', output,
            '--system-prompt', '', '--tools', tools, '--allowedTools', allowed])

    def test_native_research_text_output_and_web_tools_are_accepted(self):
        args = self.arguments(output='text', tools='WebSearch,WebFetch', allowed='WebSearch,WebFetch')
        _validate_arguments(args)
        self.assertEqual(args.output_format, 'text')

    def test_tool_free_json_contract_remains_accepted(self):
        _validate_arguments(self.arguments())
        _validate_arguments(self.arguments(allowed='Read'))

    def test_arbitrary_and_mismatched_tools_refuse(self):
        for tools, allowed in [('Bash', 'Bash'), ('WebSearch,WebFetch', 'Bash'),
                ('Bash', 'WebSearch,WebFetch'), ('', 'WebSearch,WebFetch')]:
            with self.subTest(tools=tools, allowed=allowed), self.assertRaises(ValueError):
                _validate_arguments(self.arguments(tools=tools, allowed=allowed))
