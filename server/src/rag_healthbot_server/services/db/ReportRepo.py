from rag_healthbot_server import db
from rag_healthbot_server.Models.Report import IReport, Report
from pydantic import validate_call


@validate_call
def create_report(data: IReport):
    _data = Report(**data.model_dump())
    db.session.add(_data)
    db.session.commit()
    return _data
    pass


def get_report(report_id: int):
    pass


def list_reports():
    pass


def delete_report(report_id: int):
    pass


def update_report(report_id: int, data):
    pass
