# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Viewer Simple (porte d omega-serv le 2026-11-21), retour utilisateur 2026-11-20 : colonne Service (l'heure d'une date syslog etait prise pour le
service), couleurs de la colonne Message (variables du theme), ligne entiere."""
import unittest

from omega_fire.domain.log_stats.parser import extract_service, parse_log_line
from omega_fire.interfaces.tui.screens.log_line_highlight import (
    highlight_log_line,
    palette_from_theme,
)

ACCESS = ('203.0.113.7 - - [16/Nov/2026:02:48:52 +0000] "GET /a.png HTTP/1.1" 404 1076 "http://exemple.test/" '
          '"Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0" b4215a258ff34099')
SYSLOG = "Nov 20 10:00:00 machine sshd[123]: Failed password for root from 198.51.100.4 port 22 ssh2"


def _spans(line: str) -> dict[str, str]:
    text = highlight_log_line(line, palette_from_theme({"text-accent": "#FFC473", "text-warning": "#FFC400"}))
    return {line[span.start:span.end]: str(span.style) for span in text.spans}


class TestServiceColumn(unittest.TestCase):
    def test_syslog_tag_not_the_hour(self):
        self.assertEqual(extract_service(SYSLOG), "sshd")
        self.assertEqual(extract_service("2026-11-20T10:00:00 machine nginx: debut"), "nginx")
        self.assertEqual(extract_service("Nov 20 10:00:00 machine kernel: [12.3] x"), "kernel")

    def test_no_service_for_access_or_omega_serv_lines(self):
        self.assertIsNone(extract_service(ACCESS))
        self.assertIsNone(extract_service("[2026-11-20 20:47:54] administration web : ecoute sur http://127.0.0.1:1/"))


class TestMessageColours(unittest.TestCase):
    def test_access_line_parts(self):
        spans = _spans(ACCESS)
        self.assertEqual(spans["203.0.113.7"], "bold #ffc473")
        self.assertIn("[16/Nov/2026:02:48:52 +0000]", spans)
        self.assertIn("GET", spans)
        self.assertEqual(spans["404"], "bold #ffc400")
        self.assertIn("italic", spans['"Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0"'])
        self.assertEqual(spans[" b4215a258ff34099"], "dim")

    def test_syslog_parts(self):
        spans = _spans(SYSLOG)
        self.assertIn("Nov 20 10:00:00", spans)
        self.assertIn("sshd[123]:", spans)
        self.assertIn("198.51.100.4", spans)

    def test_line_is_never_markup(self):
        line = "[2026-11-20 10:00:00] [bold red]x[/] from 192.0.2.1"
        self.assertEqual(highlight_log_line(line, palette_from_theme({})).plain, line)

    def test_whole_line_kept(self):
        self.assertEqual(parse_log_line(ACCESS).message, ACCESS)


if __name__ == "__main__":
    unittest.main()
