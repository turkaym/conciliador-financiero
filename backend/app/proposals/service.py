from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import BankMovement, ImportBatch, ImportedRecord, Receipt, Reconciliation, ReconciliationProposal
from app.proposals.matching import MatchInput, RULE_VERSION, NORMALIZER_VERSION, evaluation_fingerprint, evaluate_pair, rank_matches


def _reference(record: ImportedRecord) -> str | None:
    value = record.original_data.get("referencia")
    return value if isinstance(value, str) else None


def _active_reconciliation(record_id: int):
    return select(Reconciliation.id).where(
        Reconciliation.status == "ACTIVA",
        or_(Reconciliation.movement_id == record_id, Reconciliation.receipt_id == record_id),
    ).exists()


def generate_for_batch(db: Session, batch_id: int, owner_id: int) -> list[ReconciliationProposal]:
    batch = db.scalar(select(ImportBatch).where(ImportBatch.id == batch_id, ImportBatch.user_id == owner_id))
    if batch is None or batch.status not in {"PROCESADO", "PROCESADO_CON_ERRORES"}:
        return []

    records = db.scalars(
        select(ImportedRecord)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .where(ImportedRecord.batch_id == batch_id, ImportedRecord.status == "PENDIENTE", ImportBatch.user_id == owner_id)
        .order_by(ImportedRecord.id)
    ).all()
    generated = _generate_for_records(db, records, owner_id, "LOTE", batch_id, None)
    db.flush()
    return generated


def _generate_for_records(
    db: Session,
    records: list[ImportedRecord],
    owner_id: int,
    origin_type: str,
    origin_batch_id: int | None,
    reverted_reconciliation_id: int | None,
) -> list[ReconciliationProposal]:
    movements = {row.record_id: (record, row) for record, row in db.execute(
        select(ImportedRecord, BankMovement).join(BankMovement, BankMovement.record_id == ImportedRecord.id)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .where(ImportBatch.user_id == owner_id, ImportedRecord.status.in_(("PENDIENTE", "CON_PROPUESTAS")), ~_active_reconciliation(ImportedRecord.id))
    ).all()}
    receipts = {row.record_id: (record, row) for record, row in db.execute(
        select(ImportedRecord, Receipt).join(Receipt, Receipt.record_id == ImportedRecord.id)
        .join(ImportBatch, ImportBatch.id == ImportedRecord.batch_id)
        .where(ImportBatch.user_id == owner_id, ImportedRecord.status.in_(("PENDIENTE", "CON_PROPUESTAS")), ~_active_reconciliation(ImportedRecord.id))
    ).all()}

    generated: list[ReconciliationProposal] = []
    for source in records:
        pairs: list[tuple[MatchInput, object]] = []
        if source.record_type == "MOVIMIENTO" and source.id in movements:
            movement = movements[source.id][1]
            candidates = receipts.values()
            for candidate_record, receipt in candidates:
                pair = MatchInput(source.id, movement.date, movement.amount, movement.currency, _reference(source), candidate_record.id, receipt.date, receipt.amount, receipt.currency, _reference(candidate_record))
                result = evaluate_pair(pair)
                if result is not None:
                    pairs.append((pair, result))
        elif source.record_type == "COMPROBANTE" and source.id in receipts:
            receipt = receipts[source.id][1]
            candidates = movements.values()
            for candidate_record, movement in candidates:
                pair = MatchInput(candidate_record.id, movement.date, movement.amount, movement.currency, _reference(candidate_record), source.id, receipt.date, receipt.amount, receipt.currency, _reference(source))
                result = evaluate_pair(pair)
                if result is not None:
                    pairs.append((pair, result))

        result_pairs = {result: pair for pair, result in pairs}
        for result in rank_matches(list(result_pairs)):
            pair = result_pairs[result]
            fingerprint = evaluation_fingerprint(pair)
            exists = db.scalar(select(ReconciliationProposal.id).where(
                ReconciliationProposal.movement_id == pair.movement_id,
                ReconciliationProposal.receipt_id == pair.receipt_id,
                ReconciliationProposal.rule_version == RULE_VERSION,
                ReconciliationProposal.evaluation_fingerprint == fingerprint,
            ))
            if exists is not None:
                continue
            proposal = ReconciliationProposal(
                movement_id=pair.movement_id,
                receipt_id=pair.receipt_id,
                status="GENERADA",
                normalizer_version=NORMALIZER_VERSION,
                rule_version=RULE_VERSION,
                evaluation_fingerprint=fingerprint,
                origin_type=origin_type,
                origin_batch_id=origin_batch_id,
                reverted_reconciliation_id=reverted_reconciliation_id,
                reference_score=result.reference_score,
                exact_match=result.exact_match,
                day_difference=result.day_difference,
                explanation=result.explanation,
                created_at=datetime.now(timezone.utc),
            )
            db.add(proposal)
            generated.append(proposal)
            for record_id in (pair.movement_id, pair.receipt_id):
                record = db.get(ImportedRecord, record_id)
                if record is not None and record.status == "PENDIENTE":
                    record.status = "CON_PROPUESTAS"
    db.flush()
    return generated


def generate_for_reversal(
    db: Session,
    reconciliation: Reconciliation,
    owner_id: int,
    locked_record_ids: set[int],
) -> list[ReconciliationProposal]:
    movement = db.get(ImportedRecord, reconciliation.movement_id)
    if movement is None or movement.id not in locked_record_ids:
        return []
    return _generate_for_records(
        db,
        [movement],
        owner_id,
        "REVERSION",
        None,
        reconciliation.id,
    )
