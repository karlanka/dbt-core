import pytest
from dbt.tests.util import run_dbt
from tests.functional.adapter.files import (
    seeds_base_csv,
    seeds_newcolumns_csv,
    seeds_added_csv,
    ts_snapshot_sql,
)
from dbt.tests.adapter import relation_from_name, update_rows


@pytest.fixture
def seeds():
    return {
        "base.csv": seeds_base_csv,
        "newcolumns.csv": seeds_newcolumns_csv,
        "added.csv": seeds_added_csv,
    }


@pytest.fixture
def snapshots():
    return {
        "ts_snapshot.sql": ts_snapshot_sql,
    }


@pytest.fixture
def project_config_update():
    return {"name": "snapshot_strategy_timestamp"}


def check_relation_rows(project, snapshot_name, count):
    relation = relation_from_name(project.adapter, snapshot_name)
    result = project.run_sql(f"select count(*) as num_rows from {relation}", fetch="one")
    assert result[0] == count


def test_snapshot_timestamp(project):
    # seed command
    results = run_dbt(["seed"])
    assert len(results) == 3

    # snapshot command
    results = run_dbt(["snapshot"])
    assert len(results) == 1

    # snapshot has 10 rows
    check_relation_rows(project, "ts_snapshot", 10)

    # point at the "added" seed so the snapshot sees 10 new rows
    results = run_dbt(["snapshot", "--vars", "seed_name: added"])

    # snapshot now has 20 rows
    check_relation_rows(project, "ts_snapshot", 20)

    # update some timestamps in the "added" seed so the snapshot sees 10 more new rows
    update_rows_config = {
        "name": "added",
        "dst_col": "some_date",
        "clause": {
            "src_col": "some_date",
            "type": "add_timestamp",
        },
        "where": "id > 10 and id < 21",
    }
    update_rows(project.adapter, update_rows_config)

    results = run_dbt(["snapshot", "--vars", "seed_name: added"])

    # snapshot now has 30 rows
    check_relation_rows(project, "ts_snapshot", 30)

    update_rows_config = {
        "name": "added",
        "dst_col": "name",
        "clause": {
            "src_col": "name",
            "type": "add_string",
            "value": "_updated",
        },
        "where": "id < 11",
    }
    update_rows(project.adapter, update_rows_config)

    results = run_dbt(["snapshot", "--vars", "seed_name: added"])

    # snapshot still has 30 rows because timestamp not updated
    check_relation_rows(project, "ts_snapshot", 30)
