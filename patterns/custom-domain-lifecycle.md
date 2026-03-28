# Pattern: Custom Domain Lifecycle (DNS + CDN Tenant State Machine)

## Problem

Your SaaS gives each customer a managed subdomain (`p-xyz.yourdomain.net`). Now customers want to use their own domains (`www.customer.com`). This requires:

1. Creating a CDN tenant (CloudFront distribution tenant, Cloudflare custom hostname, etc.)
2. Issuing a TLS certificate for the customer's domain
3. Guiding the customer through DNS configuration
4. Verifying that DNS is correct before activating
5. Handling the many failure modes (wrong CNAME, stale DNS, conflicting records, certificate delays)

Without a clear state machine, you end up with boolean flags like `is_verified`, `is_active`, `ssl_ready` that don't compose and don't tell you *what to do next*.

## Pattern

Model the lifecycle as a **phase state machine** with explicit transitions, and separate **DNS inspection** from **CDN tenant management** behind abstract interfaces.

```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌────────┐
│ pending  │───>│ waiting_dns │───>│ dns_detected │───>│host_provisioning│───>│ active │
└─────────┘    └─────────────┘    └──────────────┘    └─────────────────┘    └────────┘
     │               │                  │                     │
     └───────────────┴──────────────────┴─────────────────────┘
                                    │
                                    ▼
                               ┌────────┐
                               │ failed │
                               └────────┘
```

### Phase Definitions

| Phase | Meaning | Next Action |
|---|---|---|
| `pending` | Custom domain requested, nothing created yet | Create CDN tenant |
| `waiting_dns` | Tenant created, waiting for customer DNS | Show DNS instructions |
| `dns_detected` | DNS records found, tenant not yet fully provisioned | Trigger tenant setup/cert |
| `host_provisioning` | DNS correct, CDN is provisioning SSL/routing | Poll and wait |
| `active` | Everything works | Done |
| `failed` | CDN rejected the domain or cert failed | Show diagnostics, allow retry |

### Phase Resolution

The phase is **computed** from the current state of the tenant and DNS, not stored directly. This prevents stale phase data.

```python
def resolve_phase(custom_hostname: dict, dns_readiness: dict | None = None) -> dict:
    status = normalize(custom_hostname.get("status"))
    ssl_status = normalize(custom_hostname.get("ssl_status"))
    tenant_created = bool(custom_hostname.get("distribution_tenant_id"))
    cname_ok = (dns_readiness or {}).get("cname_ok", False)
    txt_ok = (dns_readiness or {}).get("txt_ok", False)

    # Terminal: active
    if status == "active" and ssl_status in ("active", "issued"):
        return {"phase": "active", "message": "Custom domain is active."}

    # Terminal: failed
    if status == "failed" or ssl_status == "failed":
        return {"phase": "failed",
                "message": "Host system could not complete domain setup. Retry verify."}

    # In-progress phases
    if tenant_created and cname_ok and txt_ok:
        return {"phase": "host_provisioning",
                "message": "DNS verified. Host system is provisioning SSL."}

    if tenant_created:
        return {"phase": "tenant_created",
                "message": "Tenant created. Waiting for DNS propagation."}

    if cname_ok and txt_ok:
        return {"phase": "dns_detected",
                "message": "DNS detected. Next verify will continue activation."}

    return {"phase": "waiting_dns",
            "message": "Waiting for DNS propagation."}
```

**Key decision:** Phase is derived, not stored. You never write `phase = "waiting_dns"` to the database. You store the facts (`distribution_tenant_id`, `status`, `ssl_status`) and compute the phase. This eliminates an entire class of bugs where the stored phase gets out of sync with reality.

### DNS Inspection

Query actual DNS records and compare against expected values. Handle the many ways registrars represent records.

```python
import dns.resolver

def inspect_dns(hostname: str, expected_target: str) -> dict:
    """Check if CNAME and TXT records point to the expected target."""
    hostname = normalize_hostname(hostname)
    target = normalize_dns_value(expected_target)
    txt_host = f"_cf-challenge.{hostname}"

    cname_candidates = []
    txt_candidates = []

    # Check CNAME
    try:
        answers = dns.resolver.resolve(hostname, "CNAME")
        for rdata in answers:
            candidate = normalize_dns_value(rdata.target.to_text())
            if candidate:
                cname_candidates.append(candidate)
    except Exception:
        pass

    # Fallback: check A/AAAA canonical name (some registrars flatten CNAMEs)
    if not cname_candidates:
        for rdtype in ("A", "AAAA"):
            try:
                answer = dns.resolver.resolve(hostname, rdtype)
                canonical = getattr(answer, "canonical_name", None)
                if canonical:
                    candidate = normalize_dns_value(canonical.to_text())
                    if candidate:
                        cname_candidates.append(candidate)
            except Exception:
                pass

    # Check TXT ownership record
    try:
        answers = dns.resolver.resolve(txt_host, "TXT")
        for rdata in answers:
            chunks = getattr(rdata, "strings", [])
            raw = "".join(
                c.decode("utf-8", errors="ignore") if isinstance(c, bytes) else str(c)
                for c in chunks
            )
            candidate = normalize_dns_value(raw)
            if candidate:
                txt_candidates.append(candidate)
    except Exception:
        pass

    return {
        "hostname": hostname,
        "expected_target": target,
        "cname_candidates": cname_candidates,
        "txt_candidates": txt_candidates,
        "cname_ok": any(values_equal(c, target) for c in cname_candidates),
        "txt_ok": any(values_equal(c, target) for c in txt_candidates),
    }
```

### DNS Value Normalization

This is where most bugs live. Different registrars return values with different casing, trailing dots, and quoting:

```python
def normalize_dns_value(value: str | None) -> str:
    """Normalize a DNS value for comparison.

    Handles: trailing dots, quotes, whitespace, case.
    'example.com.' == 'example.com' == '"example.com"' == 'EXAMPLE.COM'
    """
    return (value or "").strip().strip('"').rstrip(".").lower()


def values_equal(actual: str | None, expected: str | None) -> bool:
    a = normalize_dns_value(actual)
    e = normalize_dns_value(expected)
    return bool(a and e and a == e)
```

**Learned the hard way:**
- Namecheap auto-appends the root domain to TXT record hosts. If the user enters `_cf-challenge.www.customer.com`, Namecheap makes it `_cf-challenge.www.customer.com.customer.com`. Your instructions must warn about this.
- Some registrars wrap TXT values in quotes. Others don't. Always strip quotes.
- Some DNS resolvers return CNAME targets with a trailing dot. Always strip it.
- When a CNAME is "flattened" (ANAME/ALIAS), the CNAME query returns nothing but A/AAAA queries have a `canonical_name`. Check both.

### CDN Provider Interface

Abstract the CDN operations behind an interface so you can swap providers or mock for testing:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class HostnameStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"


class SSLStatus(str, Enum):
    PENDING = "pending"
    ISSUED = "issued"
    ACTIVE = "active"
    FAILED = "failed"


@dataclass
class ValidationRecord:
    type: str   # "CNAME", "TXT"
    name: str   # "_cf-challenge.www.customer.com"
    value: str  # "d1234.cloudfront.net"


@dataclass
class HostnameResult:
    hostname: str
    hostname_id: str | None
    status: HostnameStatus
    ssl_status: SSLStatus
    validation_records: list[ValidationRecord] | None = None
    error_message: str | None = None


class CDNProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def create_custom_hostname(self, hostname: str, project_id: str) -> HostnameResult: ...

    @abstractmethod
    async def get_custom_hostname_status(self, hostname_id: str) -> HostnameResult: ...

    @abstractmethod
    async def delete_custom_hostname(self, hostname_id: str) -> bool: ...

    @abstractmethod
    async def update_kv_mapping(self, hostname: str, project_id: str) -> bool: ...

    @abstractmethod
    async def delete_kv_mapping(self, hostname: str) -> bool: ...

    @abstractmethod
    async def invalidate_cache(self, hostname: str, paths: list[str] | None = None) -> bool: ...
```

### KV-Based Hostname Routing

At the CDN edge, map `hostname -> project_id/version_id` via a key-value store (CloudFront KeyValueStore, Cloudflare KV, etc.):

```
www.customer.com  ->  deployments/proj_abc/v3
p-xyz.app.net    ->  deployments/proj_abc/v3
landing.app.net  ->  redirect:https://www.customer.com
```

The edge function reads the KV store, extracts the prefix, and serves files from that prefix in your storage backend.

**Key decisions:**
- **Hostname is the KV key**: Simple, O(1) lookup per request.
- **Value is a storage prefix, not a project ID**: The edge function doesn't need to call your API. It reads the prefix and fetches directly from S3/storage.
- **Redirect entries**: Use a `redirect:` prefix convention so the edge function can handle redirects (e.g., subdomain -> custom domain) without backend involvement.
- **ETag versioning on writes**: CloudFront KV requires ETag-based optimistic locking. Always read-then-write with the ETag.

### Validation Instructions Builder

Generate human-readable DNS instructions from the validation records:

```python
def build_instructions(hostname: str, records: list[ValidationRecord]) -> str:
    lines = [f"To activate SSL for {hostname}, add these DNS records at your registrar:", ""]

    for rec in records:
        lines.append(f"  Type: {rec.type}")
        lines.append(f"  Name: {rec.name}")
        lines.append(f"  Value: {rec.value}")
        lines.append("")

    # Warn about registrar auto-appending
    has_txt = any(r.type == "TXT" and r.name.startswith("_cf-challenge.") for r in records)
    if has_txt:
        # Extract the part before the root domain
        labels = hostname.split(".")
        short_host = f"_cf-challenge.{'.'.join(labels[:-2])}" if len(labels) > 2 else "_cf-challenge"
        lines.append(
            f"If your registrar auto-appends your root domain, "
            f"enter `{short_host}` for the TXT host instead."
        )
        lines.append("")

    lines.append("After adding records, click Verify. DNS can take up to 24 hours.")
    return "\n".join(lines)
```

### Handling `CNAMEAlreadyExists`

When a customer's domain is already associated with another CDN resource (common during migrations), the CDN rejects the new tenant. Don't treat this as terminal failure:

```python
async def create_or_reuse_tenant(self, hostname: str, project_id: str) -> HostnameResult:
    try:
        return await self.cdn.create_custom_hostname(hostname, project_id)
    except CNAMEAlreadyExists:
        # Try to find and reuse the existing tenant
        existing = await self.cdn.find_tenant_by_hostname(hostname)
        if existing:
            return existing
        # If we can't find it, it's in another account — truly failed
        return HostnameResult(
            hostname=hostname,
            hostname_id=None,
            status=HostnameStatus.FAILED,
            ssl_status=SSLStatus.FAILED,
            error_message=f"{hostname} is already associated with another resource.",
        )
```

### The Verify Flow

The customer clicks "Verify" after adding DNS records. This triggers:

```python
async def verify_custom_domain(self, project_id: str) -> CustomDomainStatus:
    hostname_record = await self.store.get_custom_hostname(project_id)

    # 1. Inspect current DNS
    dns = inspect_dns(hostname_record["hostname"], self.expected_cname_target)

    # 2. If tenant doesn't exist yet and DNS is ready, create it
    if not hostname_record.get("distribution_tenant_id") and dns["cname_ok"]:
        result = await self.cdn.create_custom_hostname(
            hostname_record["hostname"], project_id
        )
        await self.store.update_custom_hostname(project_id, tenant_id=result.hostname_id, ...)

    # 3. If tenant exists, check its status
    elif hostname_record.get("distribution_tenant_id"):
        result = await self.cdn.get_custom_hostname_status(
            hostname_record["distribution_tenant_id"]
        )
        await self.store.update_custom_hostname(project_id, status=result.status, ...)

        # 4. If active, update KV routing
        if result.status == HostnameStatus.ACTIVE:
            await self.cdn.update_kv_mapping(
                hostname_record["hostname"], project_id
            )

    # 5. Compute and return phase
    updated = await self.store.get_custom_hostname(project_id)
    return build_status(updated, dns)
```

### Auto-Deploy on Activation

When a custom domain becomes active, automatically deploy the latest version if none is deployed yet:

```python
if result.status == HostnameStatus.ACTIVE and not await self.store.get_latest_deployment(project_id):
    latest_version = await self.store.get_latest_version(project_id)
    if latest_version:
        await self.deploy(project_id, latest_version["id"])
```

## Data Model

```python
class CustomHostname(Base):
    __tablename__ = "custom_hostnames"

    id = Column(Integer, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), unique=True)
    hostname = Column(String, nullable=False)
    distribution_tenant_id = Column(String, nullable=True)  # CDN-specific ID
    cdn_provider = Column(String, default="cloudfront")
    status = Column(String, default="pending")
    ssl_status = Column(String, default="pending")
    cname_target = Column(String, nullable=True)
    validation_records = Column(JSON, default=list)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
```

**Key decision:** Store `distribution_tenant_id` as a nullable string, not as a boolean `has_tenant`. The ID is needed for all subsequent CDN API calls (status check, delete, update).

## Pitfalls

1. **Storing phase directly**: If you write `phase = "active"` to the DB and the CDN later revokes the cert, your DB says "active" while the domain is down. Always derive phase from the raw status fields.

2. **DNS check without normalization**: `"example.com."` != `"example.com"` in string comparison. Always strip trailing dots, quotes, and lowercase before comparing.

3. **Treating `CNAMEAlreadyExists` as terminal**: This often means the customer is migrating from another setup in the same CDN account. Look for the existing tenant and reuse it.

4. **Not warning about registrar quirks**: Namecheap, GoDaddy, and Cloudflare registrars all handle TXT host fields differently. Your instructions must include the "if your registrar auto-appends" warning.

5. **Subdomain-only enforcement**: Apex domains (bare `customer.com`) can't have CNAME records (per RFC). Always enforce that custom domains are subdomains (`www.customer.com`). Default bare domain input to `www.` prefix.

6. **KV mapping before SSL is active**: If you route traffic to the custom domain before the cert is issued, visitors get SSL errors. Only update KV mapping after the status is `active`.

7. **No idempotency on domain setup**: A user clicking "Verify" 5 times shouldn't create 5 CDN tenants. Check for existing tenant before creating.

## When NOT to Use This Pattern

- **Internal tools**: If only your team uses custom domains, you can configure them manually. This pattern is for self-service customer domain setup.
- **DNS-only (no CDN)**: If you don't need a CDN tenant (just DNS pointing to your server), you can skip the CDN provider abstraction and just verify DNS records.
- **Wildcard domains only**: If you serve all customers on `*.yourdomain.net` with no custom domains, none of this applies.

## Adapting This Pattern

| If you're using... | Replace... |
|---|---|
| Cloudflare for SaaS instead of CloudFront | The CDN provider implementation. The interface, state machine, and DNS inspection stay the same. |
| Caddy/Traefik with auto-TLS | The CDN provider with a Caddy/Traefik API client. Phase machine simplifies (no separate cert provisioning step). |
| Route53 for DNS verification | The `dns.resolver` calls with Route53 API calls. Faster and more reliable than public DNS resolution. |
| A UI wizard instead of "click Verify" | Add auto-polling on the frontend that calls verify every 10-30 seconds while phase is `waiting_dns` or `host_provisioning`. |
