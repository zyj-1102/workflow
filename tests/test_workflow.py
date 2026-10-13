"""Tests for the Code Review Workflow.

Run with:  python -m pytest tests/test_workflow.py -v
       or:  python tests/test_workflow.py
"""

import sys
import os
import unittest

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import Workflow, WorkflowState, Message, MessageType
from agents import CodingAgent, ReviewAgent, FixAgent
from llm.mock_client import MockLLMClient


class TestMessage(unittest.TestCase):
    """Tests for the Message class."""

    def test_message_creation(self):
        msg = Message(sender="A", receiver="B", content="hello")
        self.assertEqual(msg.sender, "A")
        self.assertEqual(msg.receiver, "B")
        self.assertEqual(msg.content, "hello")
        self.assertEqual(msg.msg_type, MessageType.TASK)
        self.assertTrue(len(msg.msg_id) > 0)

    def test_message_to_dict(self):
        msg = Message(sender="A", receiver="B", content="hello", msg_type=MessageType.FEEDBACK)
        d = msg.to_dict()
        self.assertEqual(d["sender"], "A")
        self.assertEqual(d["receiver"], "B")
        self.assertEqual(d["msg_type"], "feedback")


class TestWorkflowState(unittest.TestCase):
    """Tests for the WorkflowState class."""

    def test_get_set(self):
        state = WorkflowState()
        state.set("code", "print('hello')")
        self.assertEqual(state.get("code"), "print('hello')")
        self.assertIsNone(state.get("nonexistent"))
        self.assertEqual(state.get("nonexistent", "default"), "default")

    def test_add_message(self):
        state = WorkflowState()
        msg = Message(sender="A", receiver="B", content="test")
        state.add_message(msg)
        self.assertEqual(len(state.messages), 1)
        self.assertEqual(state.messages[0].content, "test")

    def test_get_messages_from(self):
        state = WorkflowState()
        state.add_message(Message(sender="A", receiver="B", content="m1"))
        state.add_message(Message(sender="B", receiver="A", content="m2"))
        state.add_message(Message(sender="A", receiver="C", content="m3"))
        from_a = state.get_messages_from("A")
        self.assertEqual(len(from_a), 2)

    def test_mark_completed(self):
        state = WorkflowState()
        state.mark_completed()
        self.assertEqual(state.status, "completed")
        self.assertIsNotNone(state.finished_at)

    def test_to_json(self):
        state = WorkflowState()
        state.set("key", "value")
        json_str = state.to_json()
        self.assertIn("key", json_str)
        self.assertIn("value", json_str)


class TestMockLLM(unittest.TestCase):
    """Tests for the MockLLMClient."""

    def setUp(self):
        self.mock = MockLLMClient()

    def test_coding_response(self):
        coding_prompt = "You are a Python Coding Agent. Write code."
        code = self.mock.chat(coding_prompt, "Write Python code for is_prime")
        self.assertIn("def is_prime", code)
        # Buggy code should NOT have the n <= 1 check
        self.assertNotIn("n <= 1", code)

    def test_review_finds_bug(self):
        review_prompt = "You are a strict Python Code Reviewer."
        buggy_code = MockLLMClient.BUGGY_CODE
        result = self.mock.chat(review_prompt, f"review this code:\n{buggy_code}")
        self.assertTrue(result.strip().upper().startswith("CHANGES_REQUESTED"))

    def test_review_approves_fixed(self):
        review_prompt = "You are a strict Python Code Reviewer."
        fixed_code = MockLLMClient.FIXED_CODE
        result = self.mock.chat(review_prompt, f"review this code:\n{fixed_code}")
        self.assertTrue(result.strip().upper().startswith("APPROVED"))

    def test_fix_response(self):
        fix_prompt = "You are a Python Fix Agent."
        code = self.mock.chat(fix_prompt, "fix this code")
        self.assertIn("n <= 1", code)
        self.assertIn("def is_prime", code)


class TestAgents(unittest.TestCase):
    """Tests for individual agent behavior."""

    def setUp(self):
        self.llm = MockLLMClient()

    def test_coding_agent(self):
        agent = CodingAgent(llm=self.llm)
        state = WorkflowState(data={"requirement": "is_prime function"})
        state = agent.run(state)
        self.assertIn("code", state.data)
        self.assertIn("def is_prime", state.get("code"))
        self.assertEqual(state.get("code_version"), 1)
        self.assertEqual(len(state.messages), 1)

    def test_coding_agent_no_requirement(self):
        agent = CodingAgent(llm=self.llm)
        state = WorkflowState()
        with self.assertRaises(ValueError):
            agent.run(state)

    def test_review_agent_requests_fix(self):
        agent = ReviewAgent(llm=self.llm)
        state = WorkflowState(data={"code": MockLLMClient.BUGGY_CODE})
        state = agent.run(state)
        self.assertTrue(state.get("needs_fix"))
        self.assertFalse(state.get("approved"))
        self.assertEqual(state.get("review_count"), 1)

    def test_review_agent_approves(self):
        agent = ReviewAgent(llm=self.llm)
        state = WorkflowState(data={"code": MockLLMClient.FIXED_CODE})
        state = agent.run(state)
        self.assertFalse(state.get("needs_fix"))
        self.assertTrue(state.get("approved"))

    def test_fix_agent(self):
        agent = FixAgent(llm=self.llm)
        state = WorkflowState(
            data={
                "code": MockLLMClient.BUGGY_CODE,
                "review_result": "CHANGES_REQUESTED\nIssue: n<=1",
                "code_version": 1,
            }
        )
        state = agent.run(state)
        self.assertIn("n <= 1", state.get("code"))
        self.assertEqual(state.get("code_version"), 2)
        self.assertFalse(state.get("needs_fix"))


class TestWorkflow(unittest.TestCase):
    """Integration tests for the full workflow."""

    def setUp(self):
        self.llm = MockLLMClient()
        self.wf = Workflow("test", max_iterations=10)
        self.wf.add_step("coding", CodingAgent(llm=self.llm),
                         router=lambda s: "review", is_start=True)
        self.wf.add_step("review", ReviewAgent(llm=self.llm),
                         router=lambda s: "fix" if s.get("needs_fix") else None)
        self.wf.add_step("fix", FixAgent(llm=self.llm),
                         router=lambda s: "review")

    def test_full_workflow(self):
        state = self.wf.run({"requirement": "is_prime function"})
        self.assertEqual(state.status, "completed")
        self.assertTrue(state.get("approved"))
        self.assertEqual(state.get("review_count"), 2)
        self.assertEqual(state.get("code_version"), 2)
        self.assertEqual(state.iteration, 4)
        # Check final code is fixed
        self.assertIn("n <= 1", state.get("code"))

    def test_message_log(self):
        state = self.wf.run({"requirement": "is_prime function"})
        # 4 messages: coding->review, review->fix, fix->review, review->orchestrator
        self.assertEqual(len(state.messages), 4)
        self.assertEqual(state.messages[0].sender, "CodingAgent")
        self.assertEqual(state.messages[1].sender, "ReviewAgent")
        self.assertEqual(state.messages[2].sender, "FixAgent")
        self.assertEqual(state.messages[3].sender, "ReviewAgent")

    def test_max_iterations(self):
        wf = Workflow("test-limit", max_iterations=3)
        wf.add_step("coding", CodingAgent(llm=self.llm),
                    router=lambda s: "review", is_start=True)
        wf.add_step("review", ReviewAgent(llm=self.llm),
                    router=lambda s: "fix" if s.get("needs_fix") else None)
        wf.add_step("fix", FixAgent(llm=self.llm),
                    router=lambda s: "review")
        state = wf.run({"requirement": "is_prime"})
        # Should fail because max_iterations (3) is too low for the full cycle
        self.assertEqual(state.status, "failed")

    def test_extensibility_add_agent(self):
        """Verify that adding a new agent is straightforward."""
        from core.agent import BaseAgent

        class LoggingAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="Logger", role="Logs final result")

            def run(self, state):
                state.set("logged", True)
                return state

        wf = Workflow("extensible", max_iterations=10)
        wf.add_step("coding", CodingAgent(llm=self.llm),
                    router=lambda s: "review", is_start=True)
        wf.add_step("review", ReviewAgent(llm=self.llm),
                    router=lambda s: "fix" if s.get("needs_fix") else "log")
        wf.add_step("fix", FixAgent(llm=self.llm),
                    router=lambda s: "review")
        wf.add_step("log", LoggingAgent())  # No router → ends

        state = wf.run({"requirement": "is_prime"})
        self.assertEqual(state.status, "completed")
        self.assertTrue(state.get("logged"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
