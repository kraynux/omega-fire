Adresses complètes (format long):
2001:0db8:0000:0000:0000:0000:0000:0001
2001:0db8:85a3:0000:0000:8a2e:0370:7334
fe80:0000:0000:0000:0202:b3ff:fe1e:8329

Formes compressées (avec ::):
2001:db8::1
2001:db8:85a3::8a2e:370:7334
fe80::202:b3ff:fe1e:8329
::1
::

Adresses avec CIDR (pour tester des plages / règles réseau)
2001:db8::/32
2001:db8:abcd:0012::/64
fe80::/10
fd00:1234:5678::/48

Adresses locales / liens spéciaux (cas limites à valider)
::ffff:192.168.1.10        # IPv4-mapped IPv6
fd12:3456:789a:1::1        # ULA (Unique Local Address)
ff02::1                    # multicast (tous les nœuds du lien)
2002:c000:0204::1          # 6to4

Casse mixte (test de normalisation)
2001:DB8::1
2001:Db8:85A3::8A2E:370:7334
FE80::202:B3FF:FE1E:8329

Zéros non compressés à tester (edge cases de parsing)
2001:db8:0:0:0:0:0:1       # devrait se normaliser en 2001:db8::1
0:0:0:0:0:0:0:1            # devrait se normaliser en ::1
2001:0db8::0001            # zéros de tête à retirer



