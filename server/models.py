from pydantic import BaseModel
from typing import Optional, Literal

class RouterConfig(BaseModel):
    ip: str
    user: str = "admin"
    password: str = ""
    display_name: str = ""
    web_url: str = ""

class SitesReport(BaseModel):
    router: str
    sites: dict

class SitesRecheck(BaseModel):
    router: str
    sites: dict
    after_restart: bool = True

class SpeedReport(BaseModel):
    router: str
    vpn_down: float = 0; vpn_up: float = 0
    ru_down: float = 0; ru_up: float = 0
    ping: float = 0; ru_ping: float = 0

class WatchdogReport(BaseModel):
    router: str
    state: str = "OK"; detail: str = ""
    phase: int = 0; neo_alive: bool = True; vpn_routes: int = 0
    ip: str = ""; display_name: str = ""

class DomainGroup(BaseModel):
    name: str; entries: list[str]; policy: str
    entry_type: Literal["domain", "geosite"] = "domain"; enabled: bool = True

class IpGroup(BaseModel):
    name: str; entries: list[str]; policy: str
    entry_type: Literal["ip", "geoip"] = "ip"; enabled: bool = True

class HydraConfig(BaseModel):
    version: str = "1.0"
    domain_groups: list[DomainGroup] = []
    ip_groups: list[IpGroup] = []
