# ThreatLens source matrix

Generated from `backend/app/intelligence/catalog.py`. Inventory means the source is tracked; it does not mean the source is integrated.

Total entries: **107**.

| Category | Count |
| --- | ---: |
| Cti | 15 |
| Domain Dns | 22 |
| Infrastructure | 8 |
| Knowledge | 6 |
| Malware | 6 |
| Reputation | 9 |
| Research | 23 |
| Url Phishing | 5 |
| Vulnerability | 13 |

| Source | Category | Access | Credentials | Implementation | Test state | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| [AlienVault / LevelBlue OTX](https://otx.alienvault.com) | Cti | Otx Directconnect Api | `OTX_API_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user key | Community intelligence quality and upstream duplication require analyst review |
| [CIRCL](https://www.circl.lu) | Cti | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Configured TAXII 2.1 collections](https://docs.oasis-open.org/cti/taxii/v2.1/taxii-v2.1.html) | Cti | Taxii 2 1 Read Only | None declared | IMPLEMENTED_AND_TESTED | Fixture-tested TAXII 2.1 discovery, collections, manifest, and pagination | Read-only TAXII 2.1; supported STIX Indicator patterns only |
| [Feodo Tracker](https://feodotracker.abuse.ch) | Cti | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Local development fixtures](https://localhost.invalid/fixtures) | Cti | Local Fixture | None declared | IMPLEMENTED_AND_TESTED | Unit tested | Demonstration data only |
| [MalwareBazaar](https://bazaar.abuse.ch) | Cti | To Be Verified | `ABUSECH_AUTH_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Manual STIX 2.1 bundle import](https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html) | Cti | Manual Stix 2 1 Json | None declared | MANUAL_IMPORT_ONLY | Parser, persistence, authorization, partial-result, and deduplication tested | STIX 2.1 Indicator objects with one supported equality pattern per object |
| [MISP](https://www.misp-project.org) | Cti | Configured Misp Rest Api | `MISP_URL`, `MISP_API_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; configured server and key pending | HTTPS public host required; server sharing and distribution policy applies |
| [Pulsedive](https://pulsedive.com) | Cti | To Be Verified | `PULSEDIVE_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [SSLBL](https://sslbl.abuse.ch) | Cti | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ThreatFox](https://threatfox.abuse.ch) | Cti | Abuse Ch Community Api | `ABUSECH_AUTH_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user key | Provider matches are observations and do not establish attribution |
| [ThreatMiner](https://www.threatminer.org) | Cti | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ThreatView.io](https://threatview.io) | Cti | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [URLhaus](https://urlhaus.abuse.ch) | Cti | To Be Verified | `ABUSECH_AUTH_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [VirusTotal](https://www.virustotal.com) | Cti | Api V3 Lookup | `VIRUSTOTAL_API_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user key | Public-tier commercial-use and quota restrictions apply |
| [AFRINIC](https://www.afrinic.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [APNIC](https://www.apnic.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ARIN](https://www.arin.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [BGPView](https://bgpview.io) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Cert Spotter](https://sslmate.com/certspotter) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Certificate Transparency data](https://certificate.transparency.dev) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [crt.sh](https://crt.sh) | Domain Dns | Public Certificate Search | None declared | ADAPTER_SCAFFOLDED | Fixture-tested; bounded live endpoint validation pending | Certificate names show issuance history, not current control or attribution |
| [DNSDB](https://www.dnsdb.info) | Domain Dns | To Be Verified | `DNSDB_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [DNSDumpster](https://dnsdumpster.com) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [HackerTarget](https://hackertarget.com) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Hurricane Electric BGP Toolkit](https://bgp.he.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [IP2Location](https://www.ip2location.com) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [IPinfo](https://ipinfo.io) | Domain Dns | To Be Verified | `IPINFO_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [LACNIC](https://www.lacnic.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MaxMind GeoLite](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [RADb](https://www.radb.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [RapidDNS](https://rapiddns.io) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [RDAP](https://about.rdap.org) | Domain Dns | Public Rdap Bootstrap | None declared | ADAPTER_SCAFFOLDED | Fixture-tested; bounded live endpoint validation pending | Registration data may be redacted and does not prove operator identity |
| [RIPEstat](https://stat.ripe.net) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [SecurityTrails](https://securitytrails.com) | Domain Dns | To Be Verified | `SECURITYTRAILS_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ViewDNS](https://viewdns.info) | Domain Dns | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [WhoisXML API](https://www.whoisxmlapi.com) | Domain Dns | To Be Verified | `WHOISXML_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Censys](https://search.censys.io) | Infrastructure | Platform Host Lookup Api | `CENSYS_API_TOKEN` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user token | Available fields and quota depend on the configured Censys plan |
| [FOFA](https://en.fofa.info) | Infrastructure | To Be Verified | `FOFA_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [GreyNoise](https://www.greynoise.io) | Infrastructure | Community Ip Lookup Api | `GREYNOISE_API_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user key | Scanner context is not a maliciousness verdict |
| [LeakIX](https://leakix.net) | Infrastructure | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Netlas](https://netlas.io) | Infrastructure | To Be Verified | `NETLAS_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ONYPHE](https://www.onyphe.io) | Infrastructure | To Be Verified | `ONYPHE_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Shodan](https://www.shodan.io) | Infrastructure | Host Information Api | `SHODAN_API_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user key | Observed exposure may be stale and does not establish compromise |
| [ZoomEye](https://www.zoomeye.org) | Infrastructure | To Be Verified | `ZOOMEYE_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MITRE ATT&CK Enterprise](https://attack.mitre.org/matrices/enterprise) | Knowledge | Public Stix Bundle | None declared | PUBLIC_FEED_SUPPORTED | Fixture-tested against official STIX bundle shape | Technique context supports mapping; it does not infer observed behavior |
| [MITRE ATT&CK ICS](https://attack.mitre.org/matrices/ics) | Knowledge | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MITRE ATT&CK Mobile](https://attack.mitre.org/matrices/mobile) | Knowledge | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MITRE CAPEC](https://capec.mitre.org) | Knowledge | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MITRE CWE](https://cwe.mitre.org) | Knowledge | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MITRE D3FEND](https://d3fend.mitre.org) | Knowledge | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ANY.RUN](https://any.run) | Malware | To Be Verified | `ANYRUN_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Hatching Triage](https://tria.ge) | Malware | To Be Verified | `TRIAGE_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Hybrid Analysis](https://www.hybrid-analysis.com) | Malware | To Be Verified | `HYBRID_ANALYSIS_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Joe Sandbox](https://www.joesandbox.com) | Malware | To Be Verified | `JOE_SANDBOX_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Malpedia](https://malpedia.caad.fkie.fraunhofer.de) | Malware | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [vx-underground](https://vx-underground.org) | Malware | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [AbuseIPDB](https://www.abuseipdb.com) | Reputation | Check Api V2 | `ABUSEIPDB_API_KEY` | IMPLEMENTED_AWAITING_KEY | Fixture-tested; bounded live authentication pending user key | Community reports and confidence score require analyst context |
| [Bambenek feeds](https://www.bambenekconsulting.com) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Blocklist.de](https://www.blocklist.de) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [CINS](https://cinsscore.com) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [DShield / SANS ISC](https://www.dshield.org) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Emerging Threats / Proofpoint ET](https://rules.emergingthreats.net) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [FireHOL](https://iplists.firehol.org) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Spamhaus](https://www.spamhaus.org) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Tor exit-node feeds](https://check.torproject.org/torbulkexitlist) | Reputation | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Arctic Wolf Labs](https://arcticwolf.com/resources/blog/tag/arctic-wolf-labs) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Bitdefender Labs](https://www.bitdefender.com/en-us/blog/labs) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [CERT/CC](https://www.kb.cert.org/vuls) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Check Point Research](https://research.checkpoint.com) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [CISA advisories](https://www.cisa.gov/news-events/cybersecurity-advisories) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Cisco Talos Intelligence](https://talosintelligence.com) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [CrowdStrike](https://www.crowdstrike.com/en-us/blog/category/threat-intel-research) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Elastic Security Labs](https://www.elastic.co/security-labs) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [ESET Research](https://www.welivesecurity.com) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Fortinet FortiGuard Labs](https://www.fortinet.com/fortiguard/labs) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Google Threat Intelligence / Mandiant](https://cloud.google.com/security/resources/mandiant-reports) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Kaspersky Securelist](https://securelist.com) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Microsoft Threat Intelligence](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [National CERT/CSIRT advisories](https://www.first.org/members/teams) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Palo Alto Unit 42](https://unit42.paloaltonetworks.com) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Proofpoint](https://www.proofpoint.com/us/threat-insight) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Rapid7](https://www.rapid7.com/research) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Recorded Future public research](https://www.recordedfuture.com/research) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Secureworks CTU](https://www.secureworks.com/research) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [SentinelOne Labs](https://www.sentinelone.com/labs) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Sophos X-Ops](https://news.sophos.com/en-us/category/threat-research) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Trellix](https://www.trellix.com/blogs/research) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Trend Micro](https://www.trendmicro.com/en_us/research.html) | Research | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Cloudflare Radar](https://radar.cloudflare.com) | Url Phishing | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Google Safe Browsing](https://safebrowsing.google.com) | Url Phishing | To Be Verified | `GOOGLE_SAFE_BROWSING_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [OpenPhish](https://openphish.com) | Url Phishing | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [PhishTank](https://phishtank.org) | Url Phishing | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [urlscan.io](https://urlscan.io) | Url Phishing | Passive Search Api | `URLSCAN_API_KEY` | ADAPTER_SCAFFOLDED | Fixture-tested passive search; bounded live validation pending | Historical scan presence does not establish maliciousness |
| [CISA Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | Vulnerability | Public Json Feed | None declared | PUBLIC_FEED_SUPPORTED | Lookup and bounded feed ingestion tested; live feed verified 2026-10-22 | Presence means known exploitation; absence is not evidence of safety |
| [Exploit-DB](https://www.exploit-db.com) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [GitHub Advisory Database](https://github.com/advisories) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [GitLab Advisory Database](https://advisories.gitlab.com) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Metasploit module references](https://www.metasploit.com) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [MITRE CVE / CVE.org](https://www.cve.org) | Vulnerability | Public Cve Services Api | None declared | ADAPTER_SCAFFOLDED | Fixture-tested; bounded live endpoint validation pending | CVE publication does not establish exploitation or maliciousness |
| [Nuclei templates](https://github.com/projectdiscovery/nuclei-templates) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [NVD](https://nvd.nist.gov) | Vulnerability | Public Api With Optional Key | `NVD_API_KEY` | ADAPTER_SCAFFOLDED | Fixture-tested success, absence, throttling, authorization, and parse errors | Live validation pending network allowlist for services.nvd.nist.gov |
| [OSV.dev](https://osv.dev) | Vulnerability | Public Api | None declared | ADAPTER_SCAFFOLDED | Fixture tested; live endpoint blocked by current environment policy | Live validation pending network allowlist for api.osv.dev |
| [Packet Storm](https://packetstormsecurity.com) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Snyk public advisories](https://security.snyk.io) | Vulnerability | To Be Verified | None declared | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [VulnCheck](https://vulncheck.com) | Vulnerability | To Be Verified | `VULNCHECK_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |
| [Vulners](https://vulners.com) | Vulnerability | To Be Verified | `VULNERS_API_KEY` | INVESTIGATION_NEEDED | Not run | Provider documentation and access review required |

Provider URLs identify the intended organization or dataset. API documentation, permitted automation, commercial use, authentication, and attribution requirements remain unverified unless the row is later updated with review evidence.
