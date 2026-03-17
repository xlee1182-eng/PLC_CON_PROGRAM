from app.plc_drivers.opcua_async import AsyncOPCUAPLC
from app.plc_drivers.opcda_async import AsyncOPCDA
from app.plc_drivers.mitsubishi_async import AsyncMitsubishiPLC
from app.plc_drivers.siemens_async import AsyncSiemensPLC
from app.plc_drivers.rockwell_async import AsyncRockwellPLC


def _require(config, key):
    value = config.get(key)
    if value is None:
        raise ValueError(f"Missing required PLC config key: {key}")
    return value


def _subscription_options(config):
    sub = config.get("SUBSCRIPTION") or {}
    return {
        "subscription_mode": sub.get("MODE", "auto"),
        "active_poll_ms": sub.get("ACTIVE_POLL_MS", 100),
        "idle_poll_ms": sub.get("IDLE_POLL_MS", 1000),
        "burst_cycles": sub.get("BURST_CYCLES", 10),
    }


def _build_opcua(config):
    return AsyncOPCUAPLC(
        name=_require(config, "NAME"),
        ip=_require(config, "IP"),
        port=config.get("PORT", 4840),
        tags=config.get("TAGS"),
    )


def _build_opcda(config):
    return AsyncOPCDA(
        name=_require(config, "NAME"),
        ip=_require(config, "IP"),
        port=config.get("PORT", 0),
        prog_id=config.get("PROG_ID"),
        tags=config.get("TAGS"),
    )


def _build_mitsubishi(config):
    return AsyncMitsubishiPLC(
        name=_require(config, "NAME"),
        ip=_require(config, "IP"),
        port=config.get("PORT", 5006),
        tags=config.get("TAGS"),
        **_subscription_options(config),
    )


def _build_siemens(config):
    return AsyncSiemensPLC(
        name=_require(config, "NAME"),
        ip=_require(config, "IP"),
        port=config.get("PORT", 102),
        rack=config.get("RACK", 0),
        slot=config.get("SLOT", 1),
        tags=config.get("TAGS"),
        **_subscription_options(config),
    )


def _build_rockwell(config):
    return AsyncRockwellPLC(
        name=_require(config, "NAME"),
        ip=_require(config, "IP"),
        port=config.get("PORT", 44818),
        slot=config.get("SLOT", 0),
        path=config.get("PATH"),
        tags=config.get("TAGS"),
        **_subscription_options(config),
    )


DRIVER_BUILDERS = {
    "OPCUA": _build_opcua,
    "OPCDA": _build_opcda,
    "MITSUBISHI": _build_mitsubishi,
    "SIEMENS": _build_siemens,
    "ROCKWELL": _build_rockwell,
}


def create_driver(plc_type, plc_config):
    normalized_type = str(plc_type).upper()
    builder = DRIVER_BUILDERS.get(normalized_type)

    if builder is None:
        supported = ", ".join(sorted(DRIVER_BUILDERS.keys()))
        raise ValueError(f"Unsupported PLC type: {plc_type} (supported: {supported})")

    plc = builder(plc_config)
    plc.driver_type = normalized_type
    return plc


def supported_driver_types():
    return sorted(DRIVER_BUILDERS.keys())
