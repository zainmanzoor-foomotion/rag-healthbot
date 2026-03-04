import sys


def main():
    import uvicorn

    uvicorn.run(
        "rag_healthbot_server.main:app", host="localhost", port=8000, reload=True
    )


def backfill():
    """CLI entry-point: resolve missing CUI / ICD-10 / CPT codes for all
    diseases, procedures and medications already in the database.

    Pass ``--force`` to re-resolve ALL records, overwriting existing codes.
    """
    import logging

    force = "--force" in sys.argv

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    from rag_healthbot_server.config import settings as app_settings
    from rag_healthbot_server.utilities.icd10_lookup import set_icd10_file
    from rag_healthbot_server.utilities.cpt_lookup import set_cpt_file

    if app_settings.icd10_file:
        set_icd10_file(app_settings.icd10_file)
    if app_settings.cpt_file:
        set_cpt_file(app_settings.cpt_file)

    from rag_healthbot_server.utilities.backfill_codes import backfill_all

    if force:
        print("Running backfill with --force: re-resolving ALL records")

    results = backfill_all(force=force)

    total_updated = sum(r["updated"] for r in results.values())
    total_skipped = sum(r["skipped"] for r in results.values())
    total_failed = sum(r["failed"] for r in results.values())

    print(
        f"\nBackfill complete: {total_updated} updated, {total_skipped} skipped, {total_failed} failed"
    )
    for entity, counts in results.items():
        print(f"  {entity}: {counts}")

    sys.exit(1 if total_failed else 0)
