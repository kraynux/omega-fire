<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

❯ tree
.
├── config
│   └── omega-fire.conf
├── docs
│   ├── architecture-charte.md
│   ├── architecture.md
│   ├── architectures-rules.md
│   ├── backends.md
│   ├── capabilities.md
│   ├── decisions
│   │   ├── 001-service-manager-abstraction.md
│   │   ├── 002-capability-registry-design.md
│   │   └── 003-exception-boundaries.md
│   ├── gestion-des-exceptions-inter-couches.md
│   ├── hiéarchie-exceptions-referentiel.md
│   ├── ipv6-format-accepted.txt
│   ├── menu-tree.md
│   ├── screenshots
│   │   ├── activation-profil.png
│   │   ├── aide-context.png
│   │   ├── analyse-ip.png
│   │   ├── audit-export.png
│   │   ├── audit-html-1.png
│   │   ├── audit-html-2.png
│   │   ├── ban-fail2ban.png
│   │   ├── conntrack.png
│   │   ├── create-rule.png
│   │   ├── dashboard.png
│   │   ├── fail2ban.png
│   │   ├── gestion-ip.png
│   │   ├── inter-ip.png
│   │   ├── lister-regles.png
│   │   ├── live-logs.png
│   │   ├── log-app.png
│   │   ├── logs-lnav.png
│   │   ├── logs-tails.png
│   │   ├── menu-principal.png
│   │   ├── omega-close.png
│   │   ├── registre.png
│   │   ├── splash-burn.png
│   │   ├── splash-contrast.png
│   │   ├── splash-hack.png
│   │   ├── splash-neon.png
│   │   ├── splash-pink.png
│   │   ├── splash.png
│   │   ├── stats.png
│   │   └── verif-fail2ban.png
│   └── workflows.md
├── install.sh
├── LICENCE
├── omega-fire.sh
├── omega-fire.tar.gz
├── pyproject.toml
├── README.md
├── requirements.txt
├── src
│   └── omega_fire
│       ├── app
│       │   ├── bootstrap.py
│       │   ├── dependency_container.py
│       │   ├── __init__.py
│       │   └── lifecycle.py
│       ├── application
│       │   ├── commands
│       │   │   ├── apply_policy.py
│       │   │   ├── apply_preset_all_backends.py
│       │   │   ├── apply_preset.py
│       │   │   ├── backup_state.py
│       │   │   ├── ban_ip_all_backends.py
│       │   │   ├── ban_ip.py
│       │   │   ├── create_rule_all_backends.py
│       │   │   ├── create_rule.py
│       │   │   ├── delete_rule.py
│       │   │   ├── export_audit_report.py
│       │   │   ├── export_f2b_report.py
│       │   │   ├── export_report.py
│       │   │   ├── __init__.py
│       │   │   ├── jail_ban.py
│       │   │   ├── jail_unban.py
│       │   │   ├── manage_blocklist_file.py
│       │   │   ├── manage_jail_presets.py
│       │   │   ├── manage_live_tail_pins.py
│       │   │   ├── manage_pinned_log_paths.py
│       │   │   ├── purge_backups.py
│       │   │   ├── restore_backup.py
│       │   │   ├── restore_preset_state.py
│       │   │   ├── restore_state.py
│       │   │   ├── rotate_logs.py
│       │   │   ├── sync_backends.py
│       │   │   ├── sync_rules_from_backends.py
│       │   │   ├── unban_ip_all_backends.py
│       │   │   └── unban_ip.py
│       │   ├── dto
│       │   │   ├── __init__.py
│       │   │   ├── requests.py
│       │   │   ├── responses.py
│       │   │   └── views.py
│       │   ├── exceptions.py
│       │   ├── __init__.py
│       │   ├── pipeline
│       │   │   ├── degraded_mode.py
│       │   │   ├── executor.py
│       │   │   ├── guards
│       │   │   │   ├── capability_guard.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── permission_guard.py
│       │   │   │   └── rollback_guard.py
│       │   │   ├── hooks
│       │   │   │   ├── audit_hook.py
│       │   │   │   └── __init__.py
│       │   │   ├── __init__.py
│       │   │   ├── planner.py
│       │   │   ├── rollback.py
│       │   │   └── steps.py
│       │   └── queries
│       │       ├── app_log.py
│       │       ├── audit_report
│       │       │   ├── activity_section.py
│       │       │   ├── anomalies_section.py
│       │       │   ├── capabilities_section.py
│       │       │   ├── health_section.py
│       │       │   ├── inventory_section.py
│       │       │   ├── models.py
│       │       │   └── report_builder.py
│       │       ├── build_stats_report.py
│       │       ├── conntrack_status.py
│       │       ├── dashboard_snapshot.py
│       │       ├── dashboard_summary.py
│       │       ├── export_rules_summary.py
│       │       ├── f2b_report
│       │       │   ├── duplicates_section.py
│       │       │   ├── jails_section.py
│       │       │   ├── models.py
│       │       │   ├── report_builder.py
│       │       │   └── system_section.py
│       │       ├── find_equivalent_rules.py
│       │       ├── health_section.py
│       │       ├── __init__.py
│       │       ├── jail_status.py
│       │       ├── list_banned_ips.py
│       │       ├── list_persisted_rules.py
│       │       ├── list_rules.py
│       │       ├── log_top_ips.py
│       │       └── read_audit_history.py
│       ├── core
│       │   ├── audit.py
│       │   ├── capability.py
│       │   ├── capability_registry.py
│       │   ├── constants.py
│       │   ├── enums.py
│       │   ├── exceptions.py
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── results.py
│       │   └── stats
│       │       ├── __init__.py
│       │       └── models.py
│       ├── domain
│       │   ├── fail2ban
│       │   │   ├── exceptions.py
│       │   │   ├── filters.py
│       │   │   ├── __init__.py
│       │   │   ├── jails.py
│       │   │   ├── models.py
│       │   │   ├── service.py
│       │   │   ├── transfer.py
│       │   │   └── validation.py
│       │   ├── __init__.py
│       │   ├── ip_blacklist
│       │   │   ├── exceptions.py
│       │   │   ├── export.py
│       │   │   ├── filters.py
│       │   │   ├── __init__.py
│       │   │   ├── models.py
│       │   │   ├── service.py
│       │   │   ├── sync.py
│       │   │   └── validation.py
│       │   ├── logs
│       │   │   ├── analytics.py
│       │   │   ├── cleanup.py
│       │   │   ├── exceptions.py
│       │   │   ├── __init__.py
│       │   │   ├── models.py
│       │   │   ├── parser.py
│       │   │   ├── rotation.py
│       │   │   └── service.py
│       │   ├── monitoring
│       │   │   ├── conntrack.py
│       │   │   ├── counters.py
│       │   │   ├── __init__.py
│       │   │   ├── service.py
│       │   │   └── stats.py
│       │   ├── persistence
│       │   │   ├── backup.py
│       │   │   ├── exceptions.py
│       │   │   ├── __init__.py
│       │   │   ├── restore.py
│       │   │   ├── rotation.py
│       │   │   ├── service.py
│       │   │   └── snapshots.py
│       │   ├── reports
│       │   │   ├── builders.py
│       │   │   ├── __init__.py
│       │   │   ├── serializers.py
│       │   │   ├── service.py
│       │   │   └── templates
│       │   │       ├── audit_report.html.j2
│       │   │       ├── _base.html.j2
│       │   │       ├── conntrack_export.html.j2
│       │   │       ├── f2b_report.html.j2
│       │   │       ├── ip_export.html.j2
│       │   │       ├── _palette_light-alt.css.j2
│       │   │       ├── _palette_light-basic.css.j2
│       │   │       ├── _palette_omega-base.css.j2
│       │   │       ├── _palette_omega-burn.css.j2
│       │   │       ├── _palette_omega-neon.css.j2
│       │   │       ├── report_full.html.j2
│       │   │       ├── ruleset.html.j2
│       │   │       └── stats_report.html.j2
│       │   └── rules
│       │       ├── exceptions.py
│       │       ├── fingerprint.py
│       │       ├── __init__.py
│       │       ├── models.py
│       │       ├── policies.py
│       │       ├── presets.py
│       │       └── service.py
│       ├── infrastructure
│       │   ├── backends
│       │   │   ├── conntrack
│       │   │   │   ├── adapter.py
│       │   │   │   ├── exceptions.py
│       │   │   │   ├── __init__.py
│       │   │   │   └── parser.py
│       │   │   ├── fail2ban
│       │   │   │   ├── adapter.py
│       │   │   │   ├── exceptions.py
│       │   │   │   ├── history_reader.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── jail_mapper.py
│       │   │   │   ├── parser.py
│       │   │   │   └── service_controller.py
│       │   │   ├── ip6tables
│       │   │   │   ├── adapter.py
│       │   │   │   ├── exceptions.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── mapper.py
│       │   │   │   ├── parser.py
│       │   │   │   └── serializer.py
│       │   │   ├── iptables
│       │   │   │   ├── adapter.py
│       │   │   │   ├── exceptions.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── mapper.py
│       │   │   │   ├── parser.py
│       │   │   │   └── serializer.py
│       │   │   ├── nftables
│       │   │   │   ├── adapter.py
│       │   │   │   ├── exceptions.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── mapper.py
│       │   │   │   ├── parser.py
│       │   │   │   └── serializer.py
│       │   │   └── service_manager
│       │   │       ├── adapter.py
│       │   │       ├── detector.py
│       │   │       ├── exceptions.py
│       │   │       ├── __init__.py
│       │   │       ├── openrc.py
│       │   │       ├── runit.py
│       │   │       └── systemd.py
│       │   ├── config
│       │   │   ├── env.py
│       │   │   ├── __init__.py
│       │   │   ├── loader.py
│       │   │   ├── paths.py
│       │   │   └── settings.py
│       │   ├── exceptions.py
│       │   ├── exporters
│       │   │   ├── html_exporter.py
│       │   │   ├── __init__.py
│       │   │   ├── json_exporter.py
│       │   │   └── txt_exporter.py
│       │   ├── __init__.py
│       │   ├── lnav
│       │   │   ├── formats
│       │   │   │   └── omega_fire
│       │   │   │       ├── omega_fire_access_log.json
│       │   │   │       ├── omega_fire_error_log.json
│       │   │   │       └── omega_fire_nginx_error_log.json
│       │   │   ├── __init__.py
│       │   │   └── pty_session.py
│       │   ├── logging
│       │   │   ├── app_logger.py
│       │   │   ├── audit_logger.py
│       │   │   ├── config.py
│       │   │   ├── __init__.py
│       │   │   └── stats
│       │   │       ├── file_collector.py
│       │   │       ├── __init__.py
│       │   │       ├── log_aggregator.py
│       │   │       └── sqlite_collector.py
│       │   ├── probe
│       │   │   ├── capability_mapper.py
│       │   │   ├── command_probe.py
│       │   │   ├── exceptions.py
│       │   │   ├── __init__.py
│       │   │   ├── kernel_probe.py
│       │   │   ├── known_services.py
│       │   │   ├── network_probe.py
│       │   │   ├── results.py
│       │   │   ├── scanner.py
│       │   │   └── service_probe.py
│       │   └── storage
│       │       ├── files
│       │       │   ├── archive_store.py
│       │       │   ├── __init__.py
│       │       │   ├── json_store.py
│       │       │   ├── persistence_adapter.py
│       │       │   └── text_store.py
│       │       ├── {__init__.py}
│       │       └── sqlite
│       │           ├── connection.py
│       │           ├── exceptions.py
│       │           ├── __init__.py
│       │           ├── migrations
│       │           │   ├── {alembic.ini}
│       │           │   └── versions
│       │           │       ├── v001_initial.sql
│       │           │       ├── v002_add_metadata.sql
│       │           │       ├── v002_add_rule_tracking.sql
│       │           │       ├── v003_add_rule_interface.sql
│       │           │       ├── v004_add_rules_created_at.sql
│       │           │       └── v005_add_ban_lifecycle.sql
│       │           ├── migrations.py
│       │           ├── repositories.py
│       │           └── schema.py
│       ├── __init__.py
│       ├── interfaces
│       │   ├── cli
│       │   │   ├── actions.py
│       │   │   ├── app.py
│       │   │   ├── help_text.py
│       │   │   ├── __init__.py
│       │   │   ├── keybindings.py
│       │   │   ├── menu_builder.py
│       │   │   ├── node.py
│       │   │   ├── prompts.py
│       │   │   ├── renderers
│       │   │   │   ├── capability_view.py
│       │   │   │   ├── conntrack_view.py
│       │   │   │   ├── dashboard.py
│       │   │   │   ├── frame.py
│       │   │   │   ├── gauge.py
│       │   │   │   ├── icons.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── lnav_live.py
│       │   │   │   ├── logo ascci omega.txt
│       │   │   │   ├── logo_ascci_omega.txt
│       │   │   │   ├── logs_live.py
│       │   │   │   ├── monitoring_live.py
│       │   │   │   ├── pager.py
│       │   │   │   ├── panels.py
│       │   │   │   ├── splash.py
│       │   │   │   ├── stats
│       │   │   │   │   ├── ascii_charts.py
│       │   │   │   │   ├── daily_trend_chart.py
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   ├── kpi_cards.py
│       │   │   │   │   ├── management_panel.py
│       │   │   │   │   ├── rules_evolution_panel.py
│       │   │   │   │   └── stat_tables.py
│       │   │   │   ├── styles.py
│       │   │   │   └── tables.py
│       │   │   ├── themes
│       │   │   │   ├── base.py
│       │   │   │   ├── compatibility.py
│       │   │   │   ├── __init__.py
│       │   │   │   ├── normalization.py
│       │   │   │   ├── omega_base.py
│       │   │   │   ├── omega_burn.py
│       │   │   │   ├── omega_contrast.py
│       │   │   │   ├── omega_dark.py
│       │   │   │   ├── omega_hack.py
│       │   │   │   ├── omega_light.py
│       │   │   │   ├── omega_minimal
│       │   │   │   ├── omega_minimal.py
│       │   │   │   ├── omega_mono.py
│       │   │   │   ├── omega_neon.py
│       │   │   │   ├── omega_pink.py
│       │   │   │   ├── registry.py
│       │   │   │   └── terminal.py
│       │   │   ├── tree_builder.py
│       │   │   └── views
│       │   │       └── log_stats_view.py
│       │   ├── exceptions.py
│       │   └── __init__.py
│       ├── __main__.py
│       ├── plugins
│       │   ├── builtin
│       │   │   ├── conntrack.py
│       │   │   ├── fail2ban.py
│       │   │   ├── __init__.py
│       │   │   ├── iptables.py
│       │   │   └── nftables.py
│       │   ├── exceptions.py
│       │   ├── external
│       │   │   └── __init__.py
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── manager.py
│       ├── ports
│       │   ├── audit.py
│       │   ├── blacklist.py
│       │   ├── exporter.py
│       │   ├── fail2ban.py
│       │   ├── firewall.py
│       │   ├── __init__.py
│       │   ├── logs.py
│       │   ├── monitoring.py
│       │   ├── persistence.py
│       │   ├── plugin.py
│       │   ├── rules.py
│       │   └── system.py
│       └── shared
│           ├── exceptions.py
│           ├── formatting.py
│           ├── __init__.py
│           ├── networking.py
│           ├── parsing.py
│           ├── shell.py
│           └── utils.py
└── var
    ├── backups
    │   └── snapshots
    ├── blocklist
    │   ├── blocklist-f2b.txt
    │   └── blocklist.txt
    ├── cache
    └── exports


