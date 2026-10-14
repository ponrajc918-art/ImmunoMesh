"""Vendor command templates (Section 10) — DOCUMENTATION, not tested against real hardware.

These are illustrative command sequences a human operator or an SSHSwitchAdapter implementation
could send to common switch families. They are NOT validated against any real device in this
project (no physical switch was available) and must be reviewed before use on real equipment."""
VENDOR_TEMPLATES = {
    "cisco_ios_like": {
        "isolate_port": ["interface {port}", "shutdown"],
        "restore_port": ["interface {port}", "no shutdown"],
        "isolate_vlan": ["interface {port}", "switchport access vlan {quarantine_vlan}"],
        "restore_vlan": ["interface {port}", "switchport access vlan {original_vlan}"],
    },
    "generic_snmp": {
        "isolate_port": "set IF-MIB::ifAdminStatus.{ifindex} = down (2)",
        "restore_port": "set IF-MIB::ifAdminStatus.{ifindex} = up (1)",
    },
}
