# Copyright (c) 2022 - 2024, Oracle and/or its affiliates. All rights reserved.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl/.

"""This module tests GitHub Actions CI service."""

import os
from pathlib import Path

import pytest

from macaron import MACARON_PATH
from macaron.code_analyzer.call_graph import CallGraph
from macaron.parsers.actionparser import parse as parse_action
from macaron.slsa_analyzer.ci_service.github_actions import GHWorkflowType, GitHubActions, GitHubNode

mock_repos = Path(__file__).parent.joinpath("mock_repos")
ga_has_build_kws = mock_repos.joinpath("has_build_gh_actions")
jenkins_build = mock_repos.joinpath("has_build_jenkins")
ga_no_build_kws = mock_repos.joinpath("no_build_gh_actions")


@pytest.fixture(name="github_actions")
def github_actions_() -> GitHubActions:
    """Create a GitHubActions instance."""
    return GitHubActions()


@pytest.mark.parametrize(
    (
        "workflow_name",
        "expect",
    ),
    [
        (
            "valid1.yaml",
            [
                "GitHubNode(valid1.yaml,GHWorkflowType.INTERNAL)",
                "GitHubNode(apache/maven-gh-actions-shared/.github/workflows/maven-verify.yml@v2,GHWorkflowType.REUSABLE)",
            ],
        ),
        (
            "valid2.yaml",
            [
                "GitHubNode(valid2.yaml,GHWorkflowType.INTERNAL)",
                "GitHubNode(actions/checkout@v3,GHWorkflowType.EXTERNAL)",
                "GitHubNode(actions/cache@v3,GHWorkflowType.EXTERNAL)",
                "GitHubNode(actions/setup-java@v3,GHWorkflowType.EXTERNAL)",
            ],
        ),
    ],
    ids=[
        "Internal and reusable workflows",
        "Internal and external workflows",
    ],
)
def test_build_call_graph(github_actions: GitHubActions, workflow_name: str, expect: list[str]) -> None:
    """Test building call graphs for GitHub Actions workflows."""
    resources_dir = Path(__file__).parent.joinpath("resources", "github")

    # Parse GitHub Actions workflows.
    root = GitHubNode(name="root", node_type=GHWorkflowType.NONE, source_path="", parsed_obj={}, caller_path="")
    gh_cg = CallGraph(root, "")
    workflow_path = os.path.join(resources_dir, workflow_name)
    parsed_obj = parse_action(workflow_path, macaron_path=MACARON_PATH)

    callee = GitHubNode(
        name=os.path.basename(workflow_path),
        node_type=GHWorkflowType.INTERNAL,
        source_path=workflow_path,
        parsed_obj=parsed_obj,
        caller_path="",
    )
    root.add_callee(callee)
    github_actions.build_call_graph_from_node(callee)
    assert [str(node) for node in gh_cg.bfs()] == expect


def test_is_detected(github_actions: GitHubActions) -> None:
    """Test detecting GitHub Action config files."""
    assert github_actions.is_detected(str(ga_has_build_kws))
    assert github_actions.is_detected(str(ga_no_build_kws))
    assert not github_actions.is_detected(str(jenkins_build))


@pytest.mark.parametrize(
    "mock_repo",
    [
        ga_has_build_kws,
        ga_no_build_kws,
    ],
    ids=[
        "GH Actions with build",
        "GH Actions with no build",
    ],
)
def test_gh_get_workflows(github_actions: GitHubActions, mock_repo: Path) -> None:
    """Test detection of reachable GitHub Actions workflows."""
    expect = [str(path) for path in mock_repo.joinpath(".github", "workflows").glob("*")]
    workflows = github_actions.get_workflows(str(mock_repo))
    assert sorted(workflows) == sorted(expect)


def test_gh_get_workflows_fail_on_jenkins(github_actions: GitHubActions) -> None:
    """Assert GitHubActions workflow detection not working on Jenkins CI configuration files."""
    assert not github_actions.get_workflows(str(jenkins_build))
