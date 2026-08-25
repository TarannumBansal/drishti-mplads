"""
e-SAKSHI connector.

HONEST STATUS: As of build time we could NOT verify a public, documented
programmatic API for the e-SAKSHI portal (mplads.mospi.gov.in). e-SAKSHI is a
web dashboard used for MPLADS implementation since 1 April 2023. We do NOT invent
an endpoint and we do NOT bypass authentication/CAPTCHA.

Legitimate paths this connector supports:
  1. If MoSPI publishes MPLADS datasets on data.gov.in -> use DataGovInConnector.
  2. Official downloadable export from the e-SAKSHI dashboard -> use CSV/JSON import.
  3. If/when an official e-SAKSHI API is documented, configure its base_url + token
     here via env (ESAKSHI_API_BASE, ESAKSHI_API_TOKEN) and implement fetch().
"""
import os
from .base import BaseConnector
class ESakshiConnector(BaseConnector):
    name = "esakshi"
    API_VERIFIED = False
    def fetch(self, **kw):
        base = os.environ.get("ESAKSHI_API_BASE"); token = os.environ.get("ESAKSHI_API_TOKEN")
        if not (self.API_VERIFIED and base and token):
            raise RuntimeError(
                "Live e-SAKSHI API is not verified/configured. Import an official e-SAKSHI "
                "work-level export (CSV/JSON), or use the data.gov.in connector with a MPLADS resource id.")
        raise NotImplementedError("Configure the official e-SAKSHI API here once documented.")
