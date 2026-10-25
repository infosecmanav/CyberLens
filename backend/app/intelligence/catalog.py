from dataclasses import dataclass, field

from app.models.enums import ImplementationStatus, SourceCategory


@dataclass(frozen=True)
class CatalogSource:
    source_id: str
    name: str
    category: SourceCategory
    official_url: str
    environment_variables: tuple[str, ...] = field(default_factory=tuple)
    status: ImplementationStatus = ImplementationStatus.INVESTIGATION_NEEDED
    api_documentation_url: str | None = None
    access_method: str = "TO_BE_VERIFIED"
    auth_scheme: str = "TO_BE_VERIFIED"
    free_access_status: str = "UNVERIFIED"
    commercial_usage_status: str = "UNVERIFIED"
    terms_and_licensing_notes: str = "Requires provider documentation review."
    supported_entity_types: tuple[str, ...] = field(default_factory=tuple)
    supported_operations: tuple[str, ...] = field(default_factory=tuple)
    rate_limit_policy: dict[str, object] = field(default_factory=dict)
    caching_policy: dict[str, object] = field(default_factory=dict)
    attribution_requirements: str | None = None
    test_state: str = "Not run"
    limitation: str = "Provider documentation and access review required"


def _source(
    source_id: str,
    name: str,
    category: SourceCategory,
    official_url: str,
    *environment_variables: str,
) -> CatalogSource:
    return CatalogSource(source_id, name, category, official_url, environment_variables)


# Entries establish inventory only. Remote access, licensing, and capabilities stay unverified until
# Phase 2 research and connector tests are complete; the UI must not present these as integrations.
SOURCE_CATALOG: tuple[CatalogSource, ...] = (
    CatalogSource(
        "local-fixtures",
        "Local development fixtures",
        SourceCategory.CTI,
        "https://localhost.invalid/fixtures",
        status=ImplementationStatus.IMPLEMENTED_AND_TESTED,
        access_method="LOCAL_FIXTURE",
        auth_scheme="NONE",
        free_access_status="LOCAL_ONLY",
        commercial_usage_status="LOCAL_ONLY",
        terms_and_licensing_notes="Generated demonstration data; never external intelligence.",
        supported_entity_types=("IPV4", "DOMAIN", "URL", "SHA256", "CVE"),
        supported_operations=("lookup",),
        test_state="Unit tested",
        limitation="Demonstration data only",
    ),
    CatalogSource(
        source_id="manual-stix-2-1",
        name="Manual STIX 2.1 bundle import",
        category=SourceCategory.CTI,
        official_url="https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html",
        status=ImplementationStatus.MANUAL_IMPORT_ONLY,
        api_documentation_url="https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html",
        access_method="MANUAL_STIX_2_1_JSON",
        auth_scheme="WORKSPACE_JWT",
        free_access_status="LOCAL_IMPORT",
        commercial_usage_status="CONTENT_OWNER_POLICY_APPLIES",
        terms_and_licensing_notes=(
            "Analyst-supplied content; the caller remains responsible for its markings and "
            "sharing restrictions."
        ),
        supported_entity_types=("IPV4", "IPV6", "DOMAIN", "URL", "EMAIL", "MD5", "SHA1", "SHA256"),
        supported_operations=("import",),
        attribution_requirements="Preserve STIX producer, markings, object ID, and raw object.",
        test_state="Parser, persistence, authorization, partial-result, and deduplication tested",
        limitation="STIX 2.1 Indicator objects with one supported equality pattern per object",
    ),
    CatalogSource(
        source_id="taxii-2-1",
        name="Configured TAXII 2.1 collections",
        category=SourceCategory.CTI,
        official_url="https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1.html",
        status=ImplementationStatus.IMPLEMENTED_AND_TESTED,
        api_documentation_url="https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1.html",
        access_method="TAXII_2_1_READ_ONLY",
        auth_scheme="OPTIONAL_BEARER_TOKEN_FROM_ENVIRONMENT",
        free_access_status="SERVER_POLICY_APPLIES",
        commercial_usage_status="SERVER_AND_CONTENT_OWNER_POLICY_APPLIES",
        terms_and_licensing_notes=(
            "Administrator-configured TAXII 2.1 servers; collection owner terms apply."
        ),
        supported_entity_types=("IPV4", "IPV6", "DOMAIN", "URL", "EMAIL", "MD5", "SHA1", "SHA256"),
        supported_operations=("discover", "manifest", "poll", "import"),
        rate_limit_policy={"bounded_pages": True, "server_429_honored": True},
        attribution_requirements="Preserve STIX IDs, markings, raw objects, and collection URL.",
        test_state="Fixture-tested TAXII 2.1 discovery, collections, manifest, and pagination",
        limitation="Read-only TAXII 2.1; supported STIX Indicator patterns only",
    ),
    _source(
        "virustotal",
        "VirusTotal",
        SourceCategory.CTI,
        "https://www.virustotal.com",
        "VIRUSTOTAL_API_KEY",
    ),
    _source(
        "otx",
        "AlienVault / LevelBlue OTX",
        SourceCategory.CTI,
        "https://otx.alienvault.com",
        "OTX_API_KEY",
    ),
    _source(
        "threatfox",
        "ThreatFox",
        SourceCategory.CTI,
        "https://threatfox.abuse.ch",
        "ABUSECH_AUTH_KEY",
    ),
    _source(
        "urlhaus", "URLhaus", SourceCategory.CTI, "https://urlhaus.abuse.ch", "ABUSECH_AUTH_KEY"
    ),
    _source(
        "malwarebazaar",
        "MalwareBazaar",
        SourceCategory.CTI,
        "https://bazaar.abuse.ch",
        "ABUSECH_AUTH_KEY",
    ),
    _source("feodo-tracker", "Feodo Tracker", SourceCategory.CTI, "https://feodotracker.abuse.ch"),
    _source("sslbl", "SSLBL", SourceCategory.CTI, "https://sslbl.abuse.ch"),
    _source(
        "misp",
        "MISP",
        SourceCategory.CTI,
        "https://www.misp-project.org",
        "MISP_URL",
        "MISP_API_KEY",
    ),
    _source("circl", "CIRCL", SourceCategory.CTI, "https://www.circl.lu"),
    _source("threatminer", "ThreatMiner", SourceCategory.CTI, "https://www.threatminer.org"),
    _source(
        "pulsedive", "Pulsedive", SourceCategory.CTI, "https://pulsedive.com", "PULSEDIVE_API_KEY"
    ),
    _source("threatview", "ThreatView.io", SourceCategory.CTI, "https://threatview.io"),
    _source("cve-org", "MITRE CVE / CVE.org", SourceCategory.VULNERABILITY, "https://www.cve.org"),
    CatalogSource(
        source_id="nvd",
        name="NVD",
        category=SourceCategory.VULNERABILITY,
        official_url="https://nvd.nist.gov",
        environment_variables=("NVD_API_KEY",),
        status=ImplementationStatus.ADAPTER_SCAFFOLDED,
        api_documentation_url="https://nvd.nist.gov/developers/vulnerabilities",
        access_method="PUBLIC_API_WITH_OPTIONAL_KEY",
        auth_scheme="OPTIONAL_API_KEY_HEADER",
        free_access_status="PUBLIC_API",
        commercial_usage_status="REVIEW_NVD_TERMS",
        terms_and_licensing_notes="NVD CVE API 2.0 adapter preserves the complete source record.",
        supported_entity_types=("CVE",),
        supported_operations=("lookup",),
        rate_limit_policy={"provider_limits_apply": True},
        attribution_requirements="Attribute vulnerability records to NVD and preserve references.",
        test_state="Fixture-tested success, absence, throttling, authorization, and parse errors",
        limitation="Live validation pending network allowlist for services.nvd.nist.gov",
    ),
    CatalogSource(
        source_id="cisa-kev",
        name="CISA Known Exploited Vulnerabilities",
        category=SourceCategory.VULNERABILITY,
        official_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        status=ImplementationStatus.PUBLIC_FEED_SUPPORTED,
        api_documentation_url="https://github.com/cisagov/kev-data",
        access_method="PUBLIC_JSON_FEED",
        auth_scheme="NONE",
        free_access_status="PUBLIC_DATASET",
        commercial_usage_status="REVIEW_CISA_TERMS",
        terms_and_licensing_notes="Official CISA KEV JSON dataset; preserve CISA attribution.",
        supported_entity_types=("CVE",),
        supported_operations=("lookup", "fetch_feed"),
        caching_policy={"ttl_seconds": 900},
        attribution_requirements="Attribute the Known Exploited Vulnerabilities catalog to CISA.",
        test_state="Lookup and bounded feed ingestion tested; live feed verified 2026-10-22",
        limitation="Presence means known exploitation; absence is not evidence of safety",
    ),
    CatalogSource(
        source_id="osv",
        name="OSV.dev",
        category=SourceCategory.VULNERABILITY,
        official_url="https://osv.dev",
        status=ImplementationStatus.ADAPTER_SCAFFOLDED,
        api_documentation_url="https://google.github.io/osv.dev/api/",
        access_method="PUBLIC_API",
        auth_scheme="NONE",
        free_access_status="PUBLIC_API",
        commercial_usage_status="REVIEW_OSV_TERMS",
        terms_and_licensing_notes=(
            "API adapter is fixture-tested; deployment network access is pending."
        ),
        supported_entity_types=("CVE",),
        supported_operations=("lookup",),
        test_state="Fixture tested; live endpoint blocked by current environment policy",
        limitation="Live validation pending network allowlist for api.osv.dev",
    ),
    _source(
        "github-advisories",
        "GitHub Advisory Database",
        SourceCategory.VULNERABILITY,
        "https://github.com/advisories",
    ),
    _source(
        "gitlab-advisories",
        "GitLab Advisory Database",
        SourceCategory.VULNERABILITY,
        "https://advisories.gitlab.com",
    ),
    _source(
        "snyk-advisories",
        "Snyk public advisories",
        SourceCategory.VULNERABILITY,
        "https://security.snyk.io",
    ),
    _source(
        "vulncheck",
        "VulnCheck",
        SourceCategory.VULNERABILITY,
        "https://vulncheck.com",
        "VULNCHECK_API_KEY",
    ),
    _source(
        "vulners", "Vulners", SourceCategory.VULNERABILITY, "https://vulners.com", "VULNERS_API_KEY"
    ),
    _source("exploit-db", "Exploit-DB", SourceCategory.VULNERABILITY, "https://www.exploit-db.com"),
    _source(
        "packet-storm",
        "Packet Storm",
        SourceCategory.VULNERABILITY,
        "https://packetstormsecurity.com",
    ),
    _source(
        "nuclei-templates",
        "Nuclei templates",
        SourceCategory.VULNERABILITY,
        "https://github.com/projectdiscovery/nuclei-templates",
    ),
    _source(
        "metasploit",
        "Metasploit module references",
        SourceCategory.VULNERABILITY,
        "https://www.metasploit.com",
    ),
    _source(
        "shodan", "Shodan", SourceCategory.INFRASTRUCTURE, "https://www.shodan.io", "SHODAN_API_KEY"
    ),
    _source(
        "censys",
        "Censys",
        SourceCategory.INFRASTRUCTURE,
        "https://search.censys.io",
        "CENSYS_API_TOKEN",
    ),
    _source(
        "greynoise",
        "GreyNoise",
        SourceCategory.INFRASTRUCTURE,
        "https://www.greynoise.io",
        "GREYNOISE_API_KEY",
    ),
    _source(
        "netlas", "Netlas", SourceCategory.INFRASTRUCTURE, "https://netlas.io", "NETLAS_API_KEY"
    ),
    _source(
        "zoomeye",
        "ZoomEye",
        SourceCategory.INFRASTRUCTURE,
        "https://www.zoomeye.org",
        "ZOOMEYE_API_KEY",
    ),
    _source("fofa", "FOFA", SourceCategory.INFRASTRUCTURE, "https://en.fofa.info", "FOFA_API_KEY"),
    _source("leakix", "LeakIX", SourceCategory.INFRASTRUCTURE, "https://leakix.net"),
    _source(
        "onyphe", "ONYPHE", SourceCategory.INFRASTRUCTURE, "https://www.onyphe.io", "ONYPHE_API_KEY"
    ),
    _source("crt-sh", "crt.sh", SourceCategory.DOMAIN_DNS, "https://crt.sh"),
    _source("rdap", "RDAP", SourceCategory.DOMAIN_DNS, "https://about.rdap.org"),
    _source(
        "securitytrails",
        "SecurityTrails",
        SourceCategory.DOMAIN_DNS,
        "https://securitytrails.com",
        "SECURITYTRAILS_API_KEY",
    ),
    _source("dnsdumpster", "DNSDumpster", SourceCategory.DOMAIN_DNS, "https://dnsdumpster.com"),
    _source("rapiddns", "RapidDNS", SourceCategory.DOMAIN_DNS, "https://rapiddns.io"),
    _source("viewdns", "ViewDNS", SourceCategory.DOMAIN_DNS, "https://viewdns.info"),
    _source("hackertarget", "HackerTarget", SourceCategory.DOMAIN_DNS, "https://hackertarget.com"),
    _source(
        "whoisxml",
        "WhoisXML API",
        SourceCategory.DOMAIN_DNS,
        "https://www.whoisxmlapi.com",
        "WHOISXML_API_KEY",
    ),
    _source("dnsdb", "DNSDB", SourceCategory.DOMAIN_DNS, "https://www.dnsdb.info", "DNSDB_API_KEY"),
    _source(
        "cert-spotter", "Cert Spotter", SourceCategory.DOMAIN_DNS, "https://sslmate.com/certspotter"
    ),
    _source(
        "certificate-transparency",
        "Certificate Transparency data",
        SourceCategory.DOMAIN_DNS,
        "https://certificate.transparency.dev",
    ),
    _source("ripestat", "RIPEstat", SourceCategory.DOMAIN_DNS, "https://stat.ripe.net"),
    _source("bgpview", "BGPView", SourceCategory.DOMAIN_DNS, "https://bgpview.io"),
    _source(
        "he-bgp", "Hurricane Electric BGP Toolkit", SourceCategory.DOMAIN_DNS, "https://bgp.he.net"
    ),
    _source("arin", "ARIN", SourceCategory.DOMAIN_DNS, "https://www.arin.net"),
    _source("apnic", "APNIC", SourceCategory.DOMAIN_DNS, "https://www.apnic.net"),
    _source("afrinic", "AFRINIC", SourceCategory.DOMAIN_DNS, "https://www.afrinic.net"),
    _source("lacnic", "LACNIC", SourceCategory.DOMAIN_DNS, "https://www.lacnic.net"),
    _source("radb", "RADb", SourceCategory.DOMAIN_DNS, "https://www.radb.net"),
    _source("ipinfo", "IPinfo", SourceCategory.DOMAIN_DNS, "https://ipinfo.io", "IPINFO_API_KEY"),
    _source(
        "maxmind-geolite",
        "MaxMind GeoLite",
        SourceCategory.DOMAIN_DNS,
        "https://dev.maxmind.com/geoip/geolite2-free-geolocation-data",
    ),
    _source("ip2location", "IP2Location", SourceCategory.DOMAIN_DNS, "https://www.ip2location.com"),
    _source(
        "urlscan",
        "urlscan.io",
        SourceCategory.URL_PHISHING,
        "https://urlscan.io",
        "URLSCAN_API_KEY",
    ),
    _source("phishtank", "PhishTank", SourceCategory.URL_PHISHING, "https://phishtank.org"),
    _source("openphish", "OpenPhish", SourceCategory.URL_PHISHING, "https://openphish.com"),
    _source(
        "google-safe-browsing",
        "Google Safe Browsing",
        SourceCategory.URL_PHISHING,
        "https://safebrowsing.google.com",
        "GOOGLE_SAFE_BROWSING_API_KEY",
    ),
    _source(
        "cloudflare-radar",
        "Cloudflare Radar",
        SourceCategory.URL_PHISHING,
        "https://radar.cloudflare.com",
    ),
    _source(
        "hybrid-analysis",
        "Hybrid Analysis",
        SourceCategory.MALWARE,
        "https://www.hybrid-analysis.com",
        "HYBRID_ANALYSIS_API_KEY",
    ),
    _source("anyrun", "ANY.RUN", SourceCategory.MALWARE, "https://any.run", "ANYRUN_API_KEY"),
    _source(
        "hatching-triage",
        "Hatching Triage",
        SourceCategory.MALWARE,
        "https://tria.ge",
        "TRIAGE_API_KEY",
    ),
    _source(
        "joe-sandbox",
        "Joe Sandbox",
        SourceCategory.MALWARE,
        "https://www.joesandbox.com",
        "JOE_SANDBOX_API_KEY",
    ),
    _source(
        "malpedia", "Malpedia", SourceCategory.MALWARE, "https://malpedia.caad.fkie.fraunhofer.de"
    ),
    _source(
        "vx-underground", "vx-underground", SourceCategory.MALWARE, "https://vx-underground.org"
    ),
    _source(
        "abuseipdb",
        "AbuseIPDB",
        SourceCategory.REPUTATION,
        "https://www.abuseipdb.com",
        "ABUSEIPDB_API_KEY",
    ),
    _source("spamhaus", "Spamhaus", SourceCategory.REPUTATION, "https://www.spamhaus.org"),
    _source("blocklist-de", "Blocklist.de", SourceCategory.REPUTATION, "https://www.blocklist.de"),
    _source(
        "emerging-threats",
        "Emerging Threats / Proofpoint ET",
        SourceCategory.REPUTATION,
        "https://rules.emergingthreats.net",
    ),
    _source("dshield", "DShield / SANS ISC", SourceCategory.REPUTATION, "https://www.dshield.org"),
    _source("firehol", "FireHOL", SourceCategory.REPUTATION, "https://iplists.firehol.org"),
    _source("cins", "CINS", SourceCategory.REPUTATION, "https://cinsscore.com"),
    _source(
        "bambenek",
        "Bambenek feeds",
        SourceCategory.REPUTATION,
        "https://www.bambenekconsulting.com",
    ),
    _source(
        "tor-exit-nodes",
        "Tor exit-node feeds",
        SourceCategory.REPUTATION,
        "https://check.torproject.org/torbulkexitlist",
    ),
    _source(
        "microsoft-threat-intelligence",
        "Microsoft Threat Intelligence",
        SourceCategory.RESEARCH,
        "https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence",
    ),
    _source(
        "google-mandiant",
        "Google Threat Intelligence / Mandiant",
        SourceCategory.RESEARCH,
        "https://cloud.google.com/security/resources/mandiant-reports",
    ),
    _source(
        "cisco-talos",
        "Cisco Talos Intelligence",
        SourceCategory.RESEARCH,
        "https://talosintelligence.com",
    ),
    _source(
        "unit42",
        "Palo Alto Unit 42",
        SourceCategory.RESEARCH,
        "https://unit42.paloaltonetworks.com",
    ),
    _source(
        "crowdstrike",
        "CrowdStrike",
        SourceCategory.RESEARCH,
        "https://www.crowdstrike.com/en-us/blog/category/threat-intel-research",
    ),
    _source(
        "sentinelone-labs",
        "SentinelOne Labs",
        SourceCategory.RESEARCH,
        "https://www.sentinelone.com/labs",
    ),
    _source(
        "proofpoint",
        "Proofpoint",
        SourceCategory.RESEARCH,
        "https://www.proofpoint.com/us/threat-insight",
    ),
    _source("eset", "ESET Research", SourceCategory.RESEARCH, "https://www.welivesecurity.com"),
    _source(
        "fortiguard",
        "Fortinet FortiGuard Labs",
        SourceCategory.RESEARCH,
        "https://www.fortinet.com/fortiguard/labs",
    ),
    _source(
        "checkpoint-research",
        "Check Point Research",
        SourceCategory.RESEARCH,
        "https://research.checkpoint.com",
    ),
    _source(
        "bitdefender-labs",
        "Bitdefender Labs",
        SourceCategory.RESEARCH,
        "https://www.bitdefender.com/en-us/blog/labs",
    ),
    _source(
        "sophos-xops",
        "Sophos X-Ops",
        SourceCategory.RESEARCH,
        "https://news.sophos.com/en-us/category/threat-research",
    ),
    _source(
        "secureworks-ctu",
        "Secureworks CTU",
        SourceCategory.RESEARCH,
        "https://www.secureworks.com/research",
    ),
    _source(
        "rapid7-research", "Rapid7", SourceCategory.RESEARCH, "https://www.rapid7.com/research"
    ),
    _source(
        "elastic-security-labs",
        "Elastic Security Labs",
        SourceCategory.RESEARCH,
        "https://www.elastic.co/security-labs",
    ),
    _source(
        "trellix", "Trellix", SourceCategory.RESEARCH, "https://www.trellix.com/blogs/research"
    ),
    _source(
        "trend-micro",
        "Trend Micro",
        SourceCategory.RESEARCH,
        "https://www.trendmicro.com/en_us/research.html",
    ),
    _source(
        "kaspersky-securelist",
        "Kaspersky Securelist",
        SourceCategory.RESEARCH,
        "https://securelist.com",
    ),
    _source(
        "arctic-wolf-labs",
        "Arctic Wolf Labs",
        SourceCategory.RESEARCH,
        "https://arcticwolf.com/resources/blog/tag/arctic-wolf-labs",
    ),
    _source(
        "recorded-future",
        "Recorded Future public research",
        SourceCategory.RESEARCH,
        "https://www.recordedfuture.com/research",
    ),
    _source(
        "cisa-advisories",
        "CISA advisories",
        SourceCategory.RESEARCH,
        "https://www.cisa.gov/news-events/cybersecurity-advisories",
    ),
    _source("cert-cc", "CERT/CC", SourceCategory.RESEARCH, "https://www.kb.cert.org/vuls"),
    _source(
        "national-certs",
        "National CERT/CSIRT advisories",
        SourceCategory.RESEARCH,
        "https://www.first.org/members/teams",
    ),
    _source(
        "attack-enterprise",
        "MITRE ATT&CK Enterprise",
        SourceCategory.KNOWLEDGE,
        "https://attack.mitre.org/matrices/enterprise",
    ),
    _source(
        "attack-mobile",
        "MITRE ATT&CK Mobile",
        SourceCategory.KNOWLEDGE,
        "https://attack.mitre.org/matrices/mobile",
    ),
    _source(
        "attack-ics",
        "MITRE ATT&CK ICS",
        SourceCategory.KNOWLEDGE,
        "https://attack.mitre.org/matrices/ics",
    ),
    _source("d3fend", "MITRE D3FEND", SourceCategory.KNOWLEDGE, "https://d3fend.mitre.org"),
    _source("capec", "MITRE CAPEC", SourceCategory.KNOWLEDGE, "https://capec.mitre.org"),
    _source("cwe", "MITRE CWE", SourceCategory.KNOWLEDGE, "https://cwe.mitre.org"),
)
