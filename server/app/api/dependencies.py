from fastapi import Request
from cmflib.cmfquery import CmfQuery

def get_cmf_query(request: Request) -> CmfQuery:
    return request.app.state.cmf_query