from types import SimpleNamespace

from naas_abi.apps.nexus.apps.api.app.core.workspace_catalog_seed import (
    filter_ontology_files,
    ontology_ref_matches,
    parse_agent_ref,
    parse_ontology_ref,
    resolve_agent_ref,
    resolve_agent_refs,
    resolve_app_enabled,
)


def test_parse_agent_ref() -> None:
    assert parse_agent_ref("naas_abi AbiAgent") == ("naas_abi", "AbiAgent")
    assert parse_agent_ref("example.module ExampleAgent") == (
        "example.module",
        "ExampleAgent",
    )
    assert parse_agent_ref("AbiAgent") is None
    assert parse_agent_ref("") is None


def test_resolve_agent_ref_prefers_module_prefix() -> None:
    registry = {
        "naas_abi.agents.AbiAgent/AbiAgent": object(),
        "example.module.agents.ExampleAgent/ExampleAgent": object(),
    }
    assert (
        resolve_agent_ref("naas_abi AbiAgent", registry)
        == "naas_abi.agents.AbiAgent/AbiAgent"
    )
    assert (
        resolve_agent_ref("example.module ExampleAgent", registry)
        == "example.module.agents.ExampleAgent/ExampleAgent"
    )
    assert resolve_agent_ref("missing Agent", registry) is None


def test_resolve_agent_refs_skips_unknown() -> None:
    registry = {"naas_abi.agents.AbiAgent/AbiAgent": object()}
    assert resolve_agent_refs(
        ["naas_abi AbiAgent", "nope NopeAgent"], registry
    ) == {"naas_abi.agents.AbiAgent/AbiAgent"}


def test_resolve_app_enabled_prefers_db_then_seed() -> None:
    seed = {"example.module:dashboard"}
    stored = {"example.module:dashboard": False, "example.module:other": True}
    assert resolve_app_enabled("example.module:dashboard", stored, seed) is False
    assert resolve_app_enabled("example.module:other", stored, seed) is True
    assert resolve_app_enabled("example.module:dashboard", {}, seed) is True
    assert resolve_app_enabled("example.module:unknown", {}, seed) is False


def _ontology(
    *,
    name: str,
    path: str,
    module_name: str,
) -> SimpleNamespace:
    return SimpleNamespace(name=name, path=path, module_name=module_name)


ABI = _ontology(
    name="ABI Ontology",
    path="/app/libs/naas-abi/naas_abi/ontologies/modules/ABIOntology.ttl",
    module_name="naas abi",
)
BFO = _ontology(
    name="BFO Core",
    path="/app/libs/naas-abi-core/naas_abi_core/modules/bfo/ontologies/modules/bfo-core.ttl",
    module_name="bfo",
)


def test_parse_ontology_ref() -> None:
    assert parse_ontology_ref("naas_abi ABIOntology") == ("naas_abi", "ABIOntology")
    assert parse_ontology_ref("naas_abi:ABIOntology") == ("naas_abi", "ABIOntology")
    assert parse_ontology_ref("ABIOntology.ttl") == (None, "ABIOntology.ttl")
    assert parse_ontology_ref("") is None


def test_ontology_ref_matches_module_and_name() -> None:
    assert ontology_ref_matches("naas_abi ABIOntology", ABI) is True
    assert ontology_ref_matches("naas_abi:ABI Ontology", ABI) is True
    assert ontology_ref_matches("bfo bfo-core", BFO) is True
    assert ontology_ref_matches("ABIOntology.ttl", ABI) is True
    assert ontology_ref_matches("naas_abi ABIOntology", BFO) is False
    assert ontology_ref_matches("missing Ontology", ABI) is False


def test_filter_ontology_files_none_is_wildcard() -> None:
    items = [ABI, BFO]
    assert filter_ontology_files(items, None) == items
    assert filter_ontology_files(items, []) == []
    assert filter_ontology_files(items, ["naas_abi ABIOntology"]) == [ABI]
    assert filter_ontology_files(items, ["bfo bfo-core", "nope"]) == [BFO]


def test_workspace_seed_accepts_ontologies() -> None:
    from naas_abi.apps.nexus.apps.api.app.core.config import WorkspaceSeedConfig

    seed = WorkspaceSeedConfig(
        name="Ops",
        slug="ops",
        agents=["naas_abi AbiAgent"],
        apps=["example.module:dashboard"],
        ontologies=["naas_abi ABIOntology", "bfo bfo-core"],
    )
    assert seed.ontologies == ["naas_abi ABIOntology", "bfo bfo-core"]
    assert WorkspaceSeedConfig(name="Ops", slug="ops").ontologies is None
