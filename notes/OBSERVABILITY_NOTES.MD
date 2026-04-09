Infrastructure
DigitalOcean Droplet

4GB RAM / 2 vCPU / 25GB disk
Ubuntu 24.04
k3s v1.34.5 single node cluster
Traefik ingress built in


Applications running
AppNamespaceStatusFlaskhaasRunningMongoDBhaasRunning

Observability stack
ComponentVersionPurposePrometheusbundledMetrics scraping + storageGrafana11.4.0DashboardsLoki3.6.7Log aggregationTempo2.9.0Distributed tracingOTel CollectorcontribIngestion pointPromtailbundledPod log scrapingNode ExporterbundledHost metricsKube State Metricsbundledk8s object metrics
Grafana URL: http://grafana.146.190.174.13.nip.io
Data sources connected:

- Prometheus
- Loki
- Tempo


Problems solved
Disk pressure

Node hit 100% disk, taint blocked all scheduling
Cleaned container images with k3s crictl rmi --prune
Cleared taint manually
Currently at 91% — still needs attention

Memory pressure

Was caused by too many evicted pod corpses
Cleaned with kubectl delete pods -n haas --field-selector=status.phase=Failed
Currently at 85% — tight

Grafana version conflicts

Default install shipped Grafana 12 — incompatible with Tempo plugin
Downgraded to Grafana 11.4.0

Loki version conflict

loki-stack chart too old for Grafana 11
Upgraded to grafana/loki v3.6.7

OTel exporter

loki exporter not in contrib image
Switched to otlphttp/loki

Datasource provisioning conflict

Two default datasources conflicting
Removed Prometheus from manual provisioning
