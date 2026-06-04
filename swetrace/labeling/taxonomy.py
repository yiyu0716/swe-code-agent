FAILURE_TAXONOMY: dict[str, list[str]] = {
    "RetrievalError": ["MissingKeyFile", "MissingKeyFunction", "WrongFileFocus"],
    "ContextError": ["MissingTestContext", "NoisyContext", "StaleObservation"],
    "PlanningError": ["WrongRootCause", "IncompletePlan", "IgnoresIssueConstraint"],
    "PatchError": ["PatchApplyFail", "SyntaxError", "WrongAPIUsage", "IncompleteFix"],
    "ToolError": ["InvalidArgs", "RepeatedCall", "Timeout", "PermissionDenied"],
    "TestError": ["TestNotRun", "TestCommandWrong", "UnitTestFail"],
    "EnvironmentError": ["DependencyInstallFail", "DockerFail", "RepoSetupFail", "DatasetLoadFail"],
    "ReasoningError": ["HallucinatedFile", "HallucinatedFunction", "FalseClaimOfSuccess"],
    "RewardHacking": ["VisibleTestOnlyPatch", "TrivialPatch", "TestWeaknessExploited"],
    "OverEdit": ["TooManyFilesChanged", "UnrelatedRefactor", "LargeBehaviorChange"],
}


def is_valid_failure_label(label: str) -> bool:
    if "." not in label:
        return label in FAILURE_TAXONOMY
    major, minor = label.split(".", 1)
    return minor in FAILURE_TAXONOMY.get(major, [])
