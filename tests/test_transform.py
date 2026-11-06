from datetime import date

from scripts.transform.transform import flatten_study, parse_date, parse_min_age


def test_parse_date_partielle_completee_au_1er():
    assert parse_date("2020-03") == date(2020, 3, 1)
    assert parse_date("2020") == date(2020, 1, 1)


def test_parse_date_complete_conservee():
    assert parse_date("2020-03-15") == date(2020, 3, 15)


def test_parse_date_invalide_ou_absente():
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("bientôt") is None
    assert parse_date("2020-13") is None


def test_parse_min_age_annees():
    assert parse_min_age("18 Years") == 18
    assert parse_min_age("1 Year") == 1


def test_parse_min_age_unites_inferieures_a_l_annee():
    assert parse_min_age("6 Months") == 0
    assert parse_min_age("24 Months") == 2
    assert parse_min_age("3 Weeks") == 0


def test_parse_min_age_absent():
    assert parse_min_age("N/A") is None
    assert parse_min_age(None) is None


def _etude_complete():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "  Essai test  "},
            "statusModule": {
                "overallStatus": "COMPLETED",
                "startDateStruct": {"date": "2019-05"},
                "completionDateStruct": {"date": "2020-01-31"},
            },
            "designModule": {
                "studyType": "INTERVENTIONAL",
                "phases": ["PHASE2", "PHASE3"],
                "enrollmentInfo": {"count": 120},
            },
            "conditionsModule": {"conditions": ["Diabetes", "Obesity"]},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "CHU", "class": "OTHER"}},
            "contactsLocationsModule": {"locations": [
                {"country": "France"}, {"country": "Morocco"}, {"country": "France"}]},
            "eligibilityModule": {"minimumAge": "18 Years", "sex": "ALL"},
        },
        "hasResults": True,
    }


def test_flatten_etude_complete():
    row = flatten_study(_etude_complete())
    assert row["nct_id"] == "NCT00000001"
    assert row["title"] == "Essai test"
    assert row["start_date"] == date(2019, 5, 1)
    assert row["completion_date"] == date(2020, 1, 31)
    assert row["enrollment"] == 120
    assert row["phases"] == ["PHASE2", "PHASE3"]
    assert row["countries"] == ["France", "Morocco"]  # dédupliqués
    assert row["min_age_years"] == 18
    assert row["has_results"] is True


def test_flatten_sans_identifiant_ecartee():
    etude = _etude_complete()
    del etude["protocolSection"]["identificationModule"]["nctId"]
    assert flatten_study(etude) is None


def test_flatten_sans_titre_ecartee():
    etude = _etude_complete()
    etude["protocolSection"]["identificationModule"]["briefTitle"] = "   "
    assert flatten_study(etude) is None


def test_flatten_modules_absents_donne_des_null():
    etude = {"protocolSection": {"identificationModule": {"nctId": "NCT2", "briefTitle": "T"}}}
    row = flatten_study(etude)
    assert row["status"] is None
    assert row["start_date"] is None
    assert row["enrollment"] is None
    assert row["conditions"] == []
    assert row["countries"] == []
    assert row["has_results"] is False


def test_flatten_enrollment_invalide():
    etude = _etude_complete()
    etude["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = -5
    assert flatten_study(etude)["enrollment"] is None
