from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_create_diagnostic_session():

    with TestClient(app) as client:

        response = client.post(
            "/diagnostic-sessions/"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["session_id"]
        assert data["status"] == "created"
        assert data["asset_id"] is None


def test_legacy_device_id_request_keeps_compatibility_without_using_it_as_asset_id():
    with TestClient(app) as client:
        created = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "system"},
        )
        session_id = created.json()["session_id"]
        loaded = client.get(f"/diagnostic-sessions/{session_id}")

    assert created.status_code == 200
    assert created.json()["asset_id"] is None
    assert loaded.status_code == 200
    assert loaded.json()["device_id"] == "system"
    assert loaded.json()["asset_id"] is None


def test_explicit_unresolved_session_and_its_retest_remain_unlinked():
    with TestClient(app) as client:
        original = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "system", "create_asset": False},
        )
        retest = client.post(
            "/diagnostic-sessions/",
            json={"retest_of_session_id": original.json()["session_id"]},
        )

    assert original.status_code == retest.status_code == 200
    assert original.json()["asset_id"] is None
    assert retest.json()["asset_id"] is None


def test_new_session_can_create_an_asset_and_another_session_can_link_it():
    with TestClient(app) as client:
        first = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "system", "create_asset": True},
        )
        asset_id = first.json()["asset_id"]
        second = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "system", "asset_id": asset_id},
        )

    assert first.status_code == second.status_code == 200
    assert asset_id
    assert first.json()["asset_id"] == second.json()["asset_id"] == asset_id


def test_unknown_asset_id_is_not_treated_as_an_asset_creation_request():
    with TestClient(app) as client:
        response = client.post(
            "/diagnostic-sessions/",
            json={"asset_id": "asset-not-found"},
        )

    assert response.status_code == 400
    assert "Use create_asset=true" in response.json()["detail"]


def test_reused_session_id_is_idempotent_for_matching_asset_resolution():
    session_id = str(uuid4())
    with TestClient(app) as client:
        original = client.post(
            "/diagnostic-sessions/",
            json={
                "session_id": session_id,
                "device_id": "system",
                "create_asset": True,
            },
        )
        replay = client.post(
            "/diagnostic-sessions/",
            json={
                "session_id": session_id,
                "device_id": "system",
                "create_asset": True,
            },
        )
        matching_asset_replay = client.post(
            "/diagnostic-sessions/",
            json={
                "session_id": session_id,
                "device_id": "system",
                "asset_id": original.json()["asset_id"],
            },
        )
        legacy_replay = client.post(
            "/diagnostic-sessions/",
            json={"session_id": session_id, "device_id": "system"},
        )

    assert (
        original.status_code
        == replay.status_code
        == matching_asset_replay.status_code
        == legacy_replay.status_code
        == 200
    )
    assert replay.json()["session_id"] == original.json()["session_id"]
    assert replay.json()["asset_id"] == original.json()["asset_id"]
    assert matching_asset_replay.json()["asset_id"] == original.json()["asset_id"]
    assert legacy_replay.json()["asset_id"] == original.json()["asset_id"]


def test_reused_session_id_rejects_conflicting_explicit_asset_resolution():
    session_id = str(uuid4())
    with TestClient(app) as client:
        original = client.post(
            "/diagnostic-sessions/",
            json={
                "session_id": session_id,
                "device_id": "system",
                "create_asset": True,
            },
        )
        conflicting_asset = client.post(
            "/diagnostic-sessions/",
            json={
                "session_id": session_id,
                "asset_id": "different-asset",
            },
        )
        conflicting_unresolved = client.post(
            "/diagnostic-sessions/",
            json={
                "session_id": session_id,
                "create_asset": False,
            },
        )

    assert original.status_code == 200
    assert conflicting_asset.status_code == 400
    assert "already assigned to a different asset" in conflicting_asset.json()["detail"]
    assert conflicting_unresolved.status_code == 400
    assert "already assigned to an asset" in conflicting_unresolved.json()["detail"]


def test_retest_session_keeps_the_prior_canonical_asset():
    with TestClient(app) as client:
        original = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "system", "create_asset": True},
        )
        original_session_id = original.json()["session_id"]
        retest = client.post(
            "/diagnostic-sessions/",
            json={"retest_of_session_id": original_session_id},
        )
        matching_explicit_asset = client.post(
            "/diagnostic-sessions/",
            json={
                "retest_of_session_id": original_session_id,
                "asset_id": original.json()["asset_id"],
            },
        )

    assert original.status_code == retest.status_code == 200
    assert matching_explicit_asset.status_code == 200
    assert retest.json()["asset_id"] == original.json()["asset_id"]
    assert matching_explicit_asset.json()["asset_id"] == original.json()["asset_id"]


def test_retest_rejects_an_explicit_asset_conflicting_with_the_source():
    with TestClient(app) as client:
        original = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "system", "create_asset": True},
        )
        conflict = client.post(
            "/diagnostic-sessions/",
            json={
                "retest_of_session_id": original.json()["session_id"],
                "asset_id": "different-asset",
            },
        )

    assert conflict.status_code == 400
    assert "must use the asset_id assigned to its source session" in (
        conflict.json()["detail"]
    )


def test_retest_of_legacy_session_preserves_unresolved_asset_identity():
    with TestClient(app) as client:
        original = client.post("/diagnostic-sessions/", json={"device_id": "system"})
        retest = client.post(
            "/diagnostic-sessions/",
            json={"retest_of_session_id": original.json()["session_id"]},
        )

    assert retest.status_code == 200
    assert original.json()["asset_id"] is None
    assert retest.json()["asset_id"] is None


def test_repeated_diagnostic_execution_and_retest_create_distinct_run_ids():
    with TestClient(app) as client:
        original = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "cpu", "create_asset": True},
        )
        original_id = original.json()["session_id"]
        first = client.post(
            f"/diagnostic-sessions/{original_id}/diagnostics/cpu/cpu"
        ).json()
        second = client.post(
            f"/diagnostic-sessions/{original_id}/diagnostics/cpu/cpu"
        ).json()
        retest = client.post(
            "/diagnostic-sessions/",
            json={"retest_of_session_id": original_id},
        ).json()
        retest_result = client.post(
            f"/diagnostic-sessions/{retest['session_id']}/diagnostics/cpu/cpu"
        ).json()

    assert first["diagnostic_id"] == second["diagnostic_id"] == "cpu"
    assert len({first["run_id"], second["run_id"], retest_result["run_id"]}) == 3
    assert retest["asset_id"] == original.json()["asset_id"]


def test_finalized_session_mutations_are_rejected_without_changing_report_history():
    with TestClient(app) as client:
        created = client.post("/diagnostic-sessions/")
        session_id = created.json()["session_id"]
        client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={
                "final_disposition": "Ready for resale",
                "qa_approver": "QA",
            },
        )
        finalized = client.post(f"/diagnostic-sessions/{session_id}/finalize")
        before = client.get(f"/reports/{session_id}/revisions").json()
        attempted_edit = client.post(
            f"/diagnostic-sessions/{session_id}/manual/chassis_cosmetic",
            json={"outcome": "passed"},
        )
        after = client.get(f"/reports/{session_id}/revisions").json()
        session = client.get(f"/diagnostic-sessions/{session_id}").json()

    assert finalized.status_code == 200
    assert attempted_edit.status_code == 400
    assert "Finalized QC sessions are read-only" in attempted_edit.json()["detail"]
    assert len(before) == len(after) == 1
    assert session["technician_record"]["final_disposition"] == "Ready for resale"
    assert session["manual_results"] == {}


def test_get_diagnostic_session():

    with TestClient(app) as client:

        create_response = client.post(
            "/diagnostic-sessions/"
        )

        session_id = (
            create_response.json()[
                "session_id"
            ]
        )

        response = client.get(
            f"/diagnostic-sessions/{session_id}"
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["session_id"]
            == session_id
        )


def test_get_missing_diagnostic_session():

    with TestClient(app) as client:

        response = client.get(
            "/diagnostic-sessions/missing"
        )

        assert response.status_code == 404


def test_delete_diagnostic_session_removes_it_from_history_and_report_routes():
    with TestClient(app) as client:
        created = client.post("/diagnostic-sessions/")
        session_id = created.json()["session_id"]

        deleted = client.delete(f"/diagnostic-sessions/{session_id}")
        history = client.get("/diagnostic-sessions/")
        session = client.get(f"/diagnostic-sessions/{session_id}")
        report = client.get(f"/reports/{session_id}/json")

    assert deleted.status_code == 200
    assert deleted.json() == {"session_id": session_id, "deleted": True}
    assert all(item["session_id"] != session_id for item in history.json())
    assert session.status_code == 404
    assert report.status_code == 404


def test_execute_single_diagnostic():

    with TestClient(app) as client:

        create_response = client.post(
            "/diagnostic-sessions/",
            json={"create_asset": True},
        )

        session_id = (
            create_response.json()[
                "session_id"
            ]
        )
        asset_id = create_response.json()["asset_id"]

        response = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu"
        )

        assert (
            response.status_code
            == 200
        )

        data = response.json()

        assert (
            data["device_id"]
            == "cpu"
        )

        assert (
            data["diagnostic_type"]
            == "cpu"
        )

        assert data["diagnostic_id"] == "cpu"
        assert data["run_id"] != data["diagnostic_id"]
        assert data["asset_id"] == asset_id
        assert data["component_id"]
        assert data["test_result"]["run_id"] == data["run_id"]
        assert data["test_result"]["session_id"] == session_id
        assert data["test_result"]["asset_id"] == asset_id
        assert "logical_cores" in data["details"]
        assert "cpu_usage_percent" in data["details"]
        assert data["test_result"]["test_id"] == "cpu"
        assert data["test_result"]["scan_status"] == "success"
        assert data["test_result"]["test_status"] in {
            "passed", "failed", "warning", "error", "unsupported",
            "inconclusive", "cancelled",
        }
        assert "measurements" in data["test_result"]["evidence"]

        report_response = client.get(
            f"/reports/{session_id}/json"
        )

        assert report_response.status_code == 200
        report = report_response.json()
        assert report["asset_id"] == asset_id
        assert report["report_id"]
        assert report["revision_id"]
        assert report["data"]["cpu_result"]["details"] == data["details"]
        assert report["data"]["diagnostic_summary"]["total"] == 1
        history = client.get(f"/reports/{session_id}/revisions")
        assert history.status_code == 200
        assert history.json()[-1]["revision_id"] == report["revision_id"]
        assert all(
            revision["report_id"] == report["report_id"]
            for revision in history.json()
        )

        complete_response = client.post(
            f"/diagnostic-sessions/{session_id}/complete"
        )

        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"


def test_manual_results_are_persisted_in_session_report():
    with TestClient(app) as client:
        create_response = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "manual-test-device"},
        )
        session_id = create_response.json()["session_id"]

        catalog = client.get("/diagnostic-sessions/manual-checks")
        assert catalog.status_code == 200
        assert any(
            item["id"] == "wifi_connection"
            for item in catalog.json()["manual_checks"]
        )

        response = client.post(
            f"/diagnostic-sessions/{session_id}/manual/wifi_connection",
            json={
                "outcome": "not_applicable",
                "notes": "No Wi-Fi adapter installed; confirmed by operator.",
            },
        )
        assert response.status_code == 200
        assert response.json()["result"]["status"] == "not_applicable"

        complete = client.post(
            f"/diagnostic-sessions/{session_id}/complete"
        )
        assert complete.status_code == 200

        report = client.get(
            f"/diagnostic-sessions/{session_id}/report"
        )
        assert report.status_code == 200
        payload = report.json()
        assert payload["device_id"] == "manual-test-device"
        assert payload["data"]["manual_checks"]["wifi_connection"]["notes"] == (
            "No Wi-Fi adapter installed; confirmed by operator."
        )
        assert payload["summary"]["total"] == 1
        assert payload["summary"]["not_applicable"] == 1
        assert payload["status"] == "not_applicable"


def test_manual_result_rejects_unknown_check_and_outcome():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        unknown_check = client.post(
            f"/diagnostic-sessions/{session_id}/manual/unknown",
            json={"outcome": "passed"},
        )
        invalid_outcome = client.post(
            f"/diagnostic-sessions/{session_id}/manual/charger",
            json={"outcome": "maybe"},
        )
        assert unknown_check.status_code == 400
        assert invalid_outcome.status_code == 400


def test_initial_and_final_cosmetic_inspections_are_saved_separately():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        initial_item = {
            "name": "Top lid",
            "areas": ["A"],
            "condition": "Damaged",
            "severity": "Moderate",
            "damage_description": "Scratch near the hinge",
            "damage_location": "Upper-left corner",
            "technician_confirmed": True,
        }
        final_item = {
            **initial_item,
            "condition": "Good",
            "severity": "None",
            "damage_description": "",
            "damage_location": "",
        }

        initial = client.put(
            f"/diagnostic-sessions/{session_id}/cosmetic-inspection/initial",
            json={"items": {"top_lid": initial_item}},
        )
        final = client.put(
            f"/diagnostic-sessions/{session_id}/cosmetic-inspection/final",
            json={"items": {"top_lid": final_item}},
        )

        assert initial.status_code == 200
        assert final.status_code == 200
        session = client.get(f"/diagnostic-sessions/{session_id}").json()
        assert session["cosmetic_inspections"]["initial"]["items"]["top_lid"]["condition"] == "Damaged"
        assert session["cosmetic_inspections"]["final"]["items"]["top_lid"]["condition"] == "Good"

        report = client.get(f"/reports/{session_id}/json").json()
        assert report["data"]["cosmetic_inspections"]["initial"]["items"]["top_lid"]["condition"] == "Damaged"
        assert report["data"]["cosmetic_inspections"]["final"]["items"]["top_lid"]["condition"] == "Good"


def test_manual_scan_evidence_does_not_override_technician_decision_and_retests_are_kept():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        first = client.post(
            f"/diagnostic-sessions/{session_id}/manual/wifi_connection",
            json={
                "outcome": "failed",
                "scan_status": "success",
                "detected_devices": ["wlan0", "Factory Wi-Fi"],
                "technician_decision": "not_working",
                "evidence": {"signal_strength_dbm": -52},
                "notes": "Adapter sees the test network but cannot connect.",
            },
        )
        assert first.status_code == 200
        first_result = first.json()["test_result"]
        assert first_result["test_status"] == "failed"
        assert first_result["scan_status"] == "success"
        assert first_result["technician_decision"] == "not_working"
        assert first_result["detected_devices"] == ["wlan0", "Factory Wi-Fi"]
        assert first_result["evidence"]["signal_strength_dbm"] == -52

        second = client.post(
            f"/diagnostic-sessions/{session_id}/manual/wifi_connection",
            json={
                "outcome": "passed",
                "scan_status": "success",
                "technician_decision": "working",
            },
        )
        assert second.status_code == 200
        second_result = second.json()["test_result"]
        assert second_result["test_status"] == "passed"
        assert second_result["retest_history"][0]["test_status"] == "failed"

        report = client.get(f"/diagnostic-sessions/{session_id}/report").json()
        assert report["data"]["test_results"]["wifi_connection"] == second_result


def test_retest_session_carries_previous_result_into_retest_history():
    with TestClient(app) as client:
        original_session = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "retest-device"},
        ).json()["session_id"]
        original_result = client.post(
            f"/diagnostic-sessions/{original_session}/manual/wifi_connection",
            json={
                "outcome": "failed",
                "scan_status": "success",
                "detected_devices": ["wlan0"],
                "technician_decision": "not_working",
                "notes": "Could not connect to the test network.",
            },
        ).json()["test_result"]

        retest_session = client.post(
            "/diagnostic-sessions/",
            json={
                "device_id": "retest-device",
                "retest_of_session_id": original_session,
            },
        ).json()["session_id"]
        retest_result = client.post(
            f"/diagnostic-sessions/{retest_session}/manual/wifi_connection",
            json={
                "outcome": "passed",
                "scan_status": "success",
                "technician_decision": "working",
            },
        ).json()["test_result"]

        assert retest_result["test_status"] == "passed"
        assert retest_result["retest_history"][0]["test_status"] == (
            original_result["test_status"]
        )
        assert retest_result["retest_history"][0]["source_session_id"] == (
            original_session
        )


def test_manual_result_rejects_conflicting_test_and_technician_decisions():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        response = client.post(
            f"/diagnostic-sessions/{session_id}/manual/charger",
            json={
                "outcome": "passed",
                "technician_decision": "not_working",
            },
        )
        assert response.status_code == 400


def test_warning_test_result_is_not_counted_as_pass_or_failure():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        response = client.post(
            f"/diagnostic-sessions/{session_id}/manual/ethernet",
            json={
                "outcome": "warning",
                "scan_status": "success",
                "detected_devices": ["enp0s31f6"],
                "notes": "Link is detected but no approved network was available.",
            },
        )
        assert response.status_code == 200
        assert response.json()["test_result"]["test_status"] == "warning"

        report = client.get(f"/diagnostic-sessions/{session_id}/report").json()
        assert report["summary"]["warnings"] == 1
        assert report["summary"]["passed"] == 0
        assert report["summary"]["failed"] == 0


def test_blocked_and_not_run_manual_outcomes_are_reported_separately():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        blocked = client.post(
            f"/diagnostic-sessions/{session_id}/manual/charger",
            json={"outcome": "blocked", "notes": "Approved adapter unavailable."},
        )
        not_run = client.post(
            f"/diagnostic-sessions/{session_id}/manual/ethernet",
            json={"outcome": "not_run", "notes": "Deferred by technician."},
        )
        assert blocked.status_code == 200
        assert not_run.status_code == 200

        report = client.get(f"/diagnostic-sessions/{session_id}/report").json()
        assert report["summary"]["blocked"] == 1
        assert report["summary"]["not_run"] == 1
        assert report["summary"]["failed"] == 0


def test_station_profile_retest_and_qa_disposition_persist_in_report():
    with TestClient(app) as client:
        prior_session = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "qa-test-device"},
        ).json()["session_id"]
        created = client.post(
            "/diagnostic-sessions/",
            json={
                "device_id": "qa-test-device",
                "technician": "QA Technician",
                "station_id": "LINE-04",
                "profile_name": "manufacturing_qa",
                "retest_of_session_id": prior_session,
                "planned_diagnostics": ["cpu", "memory"],
            },
        )
        session_id = created.json()["session_id"]
        saved = client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={
                "final_disposition": "CONDITIONAL PASS",
                "qa_approver": "QA Technician",
                "final_disposition_reason": "One component is not fitted on this configuration.",
            },
        )
        assert saved.status_code == 200

        report = client.get(f"/diagnostic-sessions/{session_id}/report").json()
        assert report["data"]["intake_record"]["station_id"] == "LINE-04"
        assert report["data"]["intake_record"]["profile_name"] == "manufacturing_qa"
        assert report["data"]["intake_record"]["retest_of_session_id"] == "prior-session-123"
        assert report["data"]["intake_record"]["planned_diagnostics"] == ["cpu", "memory"]
        assert report["data"]["technician_record"]["final_disposition"] == "CONDITIONAL PASS"
        assert report["data"]["technician_record"]["qa_approver"] == "QA Technician"
        assert report["data"]["technician_record"]["qa_approved_at"]
        assert report["data"]["technician_record"]["final_disposition_reason"]
        assert report["status"] == "incomplete"
        listed = client.get("/reports/").json()
        listed_session = next(item for item in listed if item["session_id"] == session_id)
        assert listed_session["station_id"] == "LINE-04"
        assert listed_session["retest_of_session_id"] == "prior-session-123"
        assert listed_session["status"] == "incomplete"


def test_stress_duration_is_forwarded_through_session_api():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        response = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu_stress",
            json={"parameters": {"duration_seconds": 1}},
        )

        assert response.status_code == 200
        assert response.json()["details"]["duration_seconds"] == 1
        assert response.json()["details"]["cpu_cores_used"] == 1


def test_technician_record_is_in_report_with_evidence_limited_health_scores():
    with TestClient(app) as client:
        created = client.post(
            "/diagnostic-sessions/",
            json={
                "device_id": "tech-device",
                "asset_tag": "ASSET-123",
                "technician": "Alex",
                "customer_reference": "WO-55",
                "workflow_type": "refurbishment",
            },
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        cpu_result = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu"
        )
        assert cpu_result.status_code == 200

        updated = client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={
                "fault_code": "THERMAL-01",
                "observed_issue": "Intermittent thermal shutdown",
                "repair_performed": "Cleaned cooling assembly",
                "replacement_performed": "",
                "customer_notes": "Return for extended burn-in",
                "refurbishment_grade": "B",
            },
        )
        assert updated.status_code == 200

        report = client.get(
            f"/diagnostic-sessions/{session_id}/report"
        )
        payload = report.json()
        assert payload["data"]["intake_record"]["asset_tag"] == "ASSET-123"
        assert payload["data"]["technician_record"]["refurbishment_grade"] == "B"
        assert payload["data"]["technician_record"]["fault_code"] == "THERMAL-01"
        assert payload["data"]["health_analytics"]["cpu_health"]["score"] == 100
        assert payload["data"]["health_analytics"]["thermal_health"]["score"] is None
        assert (
            payload["data"]["refurbishment_recommendation"]["grade"]
            == "insufficient_data"
        )


def test_technician_record_rejects_invalid_grade_and_missing_session():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        invalid_grade = client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={"refurbishment_grade": "D"},
        )
        missing_session = client.put(
            "/diagnostic-sessions/missing/technician-record",
            json={"observed_issue": "Issue"},
        )
        assert invalid_grade.status_code == 422
        assert missing_session.status_code == 404