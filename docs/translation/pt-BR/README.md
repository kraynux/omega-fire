<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="384">
</div>

# 󰦝 OMEGA-FIRE

**Estação unificada de gerenciamento da segurança de rede**

> Desenvolvido por **kraynux** para **Omega-server** 
[https://kraynux.snake-mackarel.ts.net](https://kraynux.snake-mackarel.ts.net)

Página oficial: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Prévia: [Capturas de tela](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🌐 Documentação, exportações e interface disponíveis em **17 idiomas** — veja [Idiomas da interface](#idiomas-da-interface).  
**Idiomas:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** é um aplicativo TUI (Terminal User Interface) em Python construído com [Textual](https://github.com/Textualize/textual). Ele oferece, a partir de um terminal, uma interface única para administrar os firewalls Linux, o Fail2Ban, os endereços banidos, as regras de rede, os logs e as estatísticas do sistema.

A interface Textual é o modo de funcionamento padrão e navega por menus, formulários validados (todos os campos obrigatórios são verificados antes de continuar) e telas dedicadas, com temas, ajuda contextual e atalhos de teclado compartilhados com o resto da suíte OMEGA (omega-check, omega-deep, omega-stress...). A antiga interface [Rich](https://github.com/Textualize/rich), sequencial e conduzida pela digitação de números, continua disponível via `--legacy-cli` (veja [Inicialização](#inicialização)). 
Prévia: [Capturas de tela](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

O projeto é concebido segundo os princípios da **Clean Architecture**, com uma separação clara entre domínio de negócio, orquestração, infraestrutura e interface do usuário.

## Sumário

- [Apresentação](#apresentação)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Uso](#uso)
- [Configuração](#configuração)
- [Backends e compatibilidade](#backends-e-compatibilidade)
- [Persistência, logs e exportações](#persistência-logs-e-exportações)
- [Segurança](#segurança)
- [Testes e qualidade](#testes-e-qualidade)
- [Estado do projeto](#estado-do-projeto)
- [Desinstalação](#desinstalação)
- [Licença](#licença)

---

## Apresentação

O Omega-Fire atua como um **posto de comando local** para a segurança de rede. Ele detecta automaticamente os componentes presentes na máquina e adapta os menus às capacidades realmente disponíveis.

### Objetivos

- Reunir nftables, iptables, ip6tables e Fail2Ban em uma interface coerente.
- Facilitar a observação e a ação sobre as conexões, os banimentos e os eventos do sistema.
- Centralizar as exportações, os backups, as auditorias e o histórico das operações.
- Manter uma arquitetura testável e extensível.
- Funcionar em modo degradado quando um componente opcional estiver ausente.

### O que o Omega-Fire faz

- Detecta os backends, serviços, kernel e ferramentas disponíveis.
- Administra nftables, iptables e ip6tables quando esses componentes estão presentes.
- Gerencia os IPs banidos, individualmente ou em lote, com importação, exportação, sincronização e flush.
- Cria, lista e remove regras avançadas.
- Aplica políticas predefinidas com backup automático prévio.
- Administra os jails do Fail2Ban e seus banimentos.
- Analisa os logs ao vivo ou na forma de estatísticas.
- Oferece vigilância na forma de monitoramento.
- Usa o conntrack para exibir as conexões ativas quando ele está disponível.
- Produz exportações JSON, TXT e HTML.
- Faz backup e restaura o estado completo em arquivos `.tar.gz`.
- Registra as operações em um log do aplicativo e em uma auditoria JSON estruturada.
- Monitora os serviços e aplicativos detectados: systemd, runit, OpenRC, Docker, servidores, VNC etc.

### O que o projeto não faz

- Não substitui nftables, iptables ou Fail2Ban.
- Não constitui um firewall autônomo independente do sistema.
- Não oferece autenticação multiusuário.
- Não expõe API de rede em funcionamento normal.
- Não é um dashboard web.
- Não protege diretamente uma máquina remota a partir de outra máquina.
- Por padrão, não instala nenhum arquivo fora de sua própria pasta.
- Não garante a disponibilidade de todos os backends em todas as distribuições.

---

## Funcionalidades

### 1. Capacidades e diagnósticos

- Exibição do registro das capacidades detectadas.
- Consulta detalhada de uma capacidade por identificador.
- Nova varredura manual do sistema após a instalação de um componente.
- Consulta dos diagnósticos recentes.
- Consulta e busca no log do aplicativo.
- Exportação do estado e dos diagnósticos em JSON, TXT ou HTML.
- Categoria **Suíte omega**: omega-serv (instâncias detectadas e em execução), omega-waf (extra `magnet` ativado) e omega-jail (jails instalados), visíveis no registro, no dashboard e nos relatórios.

### 2. Gerenciamento unificado de IPs

A blacklist unificada permite trabalhar com nftables e iptables a partir de uma mesma tela.

- Banimento de um IP ou de uma lista de IPs.
- Desbanimento individual ou em lote.
- Digitação direta ou importação de um arquivo.
- Lista por backend ou visão unificada.
- Sincronização entre os backends NFTables/IPTables.
- Exportação e reimportação das listas.
- Limpeza completa de um ou vários backends.
- Suporte a IPv4 e IPv6.
- Gerenciamento dos arquivos de blocklist (`var/blocklist/`) e de seus fixados diretamente pela tela dedicada.

### 3. Gerenciamento de regras e políticas

- Assistente passo a passo para criar uma regra avançada.
- Lista das regras do sistema e das regras criadas pelo Omega-Fire.
- Remoção de uma regra por seleção.
- Limpeza automática das regras inativas na base de referência.
- Limpeza e ressincronização da base com o firewall real, com prévia e backup prévio, sem nunca modificar o próprio firewall.
- Regras de outras ferramentas (UFW, Tailscale, Docker…) identificadas pela origem: exibidas para informação, nunca removidas pelo Omega-Fire.
- Proteção antes de aplicar uma política ou esvaziar o iptables quando outras ferramentas têm regras nele: aplicar em todos, apenas no nftables, ou cancelar — consequências detalhadas na ajuda.
- Aplicação de políticas predefinidas.
- Backup automático antes da aplicação de uma política.
- Personalização, backup e restauração de uma política.
- Identificação da política ativa no menu de status e no dashboard.
- Sinalização dos perfis modificados na forma `Perfil + CUSTOM`.
- Gerenciamento das tabelas (menu 3.5): diagnóstico somente leitura por backend (presença da tabela, políticas input/output/forward, número de regras) com explicação das políticas diferentes entre backends (efeito real, causa e solução).
- Inicialização de uma tabela nftables no primeiro uso, sem jamais sobrescrever uma chain já configurada.
- Redefinição das políticas de chain para ACCEPT em um backend, para corrigir uma política restritiva órfã deixada por um perfil anterior.
- Esvaziamento direcionado de um backend ou esvaziamento sincronizado de todos os backends detectados em uma única ação.
- Remoção completa de uma tabela nftables (ação avançada, além das regras isoladas).

### 4. Gerenciamento do Fail2Ban

- Estado detalhado dos jails e de seus parâmetros.
- Número de IPs banidos e informações de rate-limit.
- Busca de um IP nos jails.
- Ban e unban individuais ou múltiplos.
- Transferência de IPs entre jails, backends e arquivos.
- Criação guiada de um jail personalizado.
- Modelos de jails predefinidos, editáveis e removíveis.
- Origem de cada jail: Omega-Fire, omega-jail, configuração principal do fail2ban ou outro arquivo.
- Remoção confiável de um jail, qualquer que seja o nome do seu arquivo: aviso para um jail instalado pelo omega-jail, recusa explicada para um jail do `jail.local` ou de um arquivo compartilhado, filtros padrão do fail2ban nunca removidos.
- Esvaziamento de um jail ou purga geral.
- Exportação em JSON, TXT ou HTML.
- Verificação e auditoria da configuração.
- Controle do serviço: status, início, parada, reinício, ativação e desativação na inicialização; após um início ou uma parada, o registro de capacidades e o dashboard são atualizados.

### 5. Logs e manutenção

- **Biblioteca de logs** (5.1): importação automática dos logs das instâncias omega-serv detectadas, incluindo os do omega-waf, fixação manual de um caminho e obtenção de um log remoto por SSH (chave ou agente, nunca senha).
- **Favoritos** (5.2): combinar logs da Biblioteca, salvá-los com um nome e um visualizador e iniciá-los diretamente.
- **Ver os logs** (5.3): um log sem configuração, com o visualizador de sua escolha — Simples (dashboard em tempo real), Clássico (últimas linhas e depois acompanhamento ao vivo) ou `lnav`.
- Integração do `lnav`: vários logs mesclados em uma única visão cronológica, encapsulada em um header/footer do Omega-Fire (veja [Navegação](#navegação)).
- Análise dos IPs mais frequentes com Top N, exportável para ser recarregada na limpeza direcionada.
- Limpeza direcionada de um ou mais IPs em arquivos LOG ou TXT, digitados à mão ou marcados a partir de uma exportação.
- Arquivos fixados com **presets para marcar**: apenas os caminhos usuais realmente presentes na máquina são propostos.
- Rotação e backups imediatos ou automatizados.
- Restauração de um backup.
- Purga por antiguidade, cota, tipo ou seleção manual.
- Limpeza avançada por pasta ou ambiente.
- Estatísticas de 24 horas, 7 dias ou 30 dias.
- Análise dos eventos, movimentos, cotas e IPs presentes nos jails.

### 6. Exportações e relatórios

Formatos disponíveis:

- **JSON**: dados estruturados e reutilizáveis.
- **TXT**: formato bruto ou adaptado para injeção.
- **HTML**: relatório legível e visual.

Relatórios disponíveis:

- Blacklist completa.
- Ruleset estruturado.
- Regras selecionadas por origem: sistema, Omega-Fire ou ativas.
- Relatório de auditoria completo.
- Estatísticas do Fail2Ban.
- Estado e diagnósticos do sistema.
- Relatórios estatísticos de 7 ou 30 dias.
- Ranking Top N dos IPs.
- Guia de ajuda e FAQ.

**Ver todas as exportações** (6.5): todos os arquivos exportados em um só lugar, com tipo, data e tamanho; um relatório HTML abre no navegador web padrão do usuário, um JSON ou TXT é lido no Omega-Fire, sem terminal nem gerenciador de arquivos.

Temas HTML:

- `omega-base` — azul-noite e ciano, tema padrão.
- `omega-burn` — brasa vermelho-alaranjada.
- `omega-neon` — cyberpunk ciano e magenta.
- `light-basic` — claro e sóbrio.
- `light-alt` — papel creme e verde-floresta.

Idioma das exportações: configurado à parte nas configurações (« Como a interface » por padrão), para entregar um relatório no idioma do seu leitor sem mudar o da interface.

### 7. Sistema e persistência

- Backup do estado completo: regras, bans do nftables, bans do iptables e Fail2Ban.
- Criação de arquivos `.tar.gz` com data e hora.
- Lista e restauração de snapshots: apenas as regras do Omega-Fire recriáveis de forma idêntica são repostas; as de outras ferramentas nunca são tocadas.
- Histórico das ações.
- Filtragem e purga do histórico.
- Recarga da configuração e nova varredura sem reinício.

### 8. Monitoramento e estatísticas

- Dashboard em tempo real com atualização periódica (a cada 2 segundos), sem bloquear a interface durante a coleta.
- Visualização da política ativa.
- Conexões ativas via conntrack.
- Tráfego, eventos, estatísticas e logs do servidor.
- Relatórios consolidados de 7 e 30 dias.
- Exportação HTML dos snapshots e relatórios.

### 9. Configurações

- Escolha do tema ativo entre os dez temas `omega-*` compartilhados com o resto da suíte (veja [Temas e terminais](#temas-e-terminais)), persistido entre duas execuções.
- Substituição manual do perfil de renderização (automático, completo, padrão, reduzido ou somente mono), aplicada na próxima execução.
- Idioma da interface entre 17 idiomas (veja [Idiomas da interface](#idiomas-da-interface)): só a interface é reiniciada; as regras do firewall, o Fail2Ban e os serviços não são afetados.
- Idioma das exportações HTML e TXT, independente do da interface.
- Pastas de exportações e de capturas de tela modificáveis, com limpeza após confirmação.
- Acessível pelo menu principal (`9. CONFIGURAÇÕES`) ou diretamente pela tecla `s`.

### 10. Ajuda

- **Guia de ajuda**: todas as fichas de ajuda reunidas na ordem dos menus, cada ficha abrindo suas fichas relacionadas.
- **FAQ**: as perguntas reais encontradas no uso (regras de outras ferramentas, restauração, Fail2Ban, logs, exportações e navegador).
- Exportação HTML do guia e da FAQ, no idioma das exportações.
- A tecla `a` continua sendo a ajuda da tela atual.

---

## Arquitetura

```text
src/omega_fire/
├── app/              Bootstrap e contêiner de injeção de dependências
├── core/             Capacidades, enumerações e exceções
├── domain/           Lógica de negócio pura: regras, IPs, jails, logs
├── application/      Orquestração: commands e queries
├── infrastructure/   Backends, armazenamento, exportações, logs e sondas do sistema
├── ports/            Contratos Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, padrão) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Extensões integradas: nftables, iptables, Fail2Ban, conntrack
└── shared/           Parsing, rede, formatação e utilitários transversais
```

### Princípios de design

- `domain/` não contém nem I/O nem dependência da infraestrutura.
- `application/` orquestra os casos de uso via domínio e ports — as telas Textual e as ações da interface Rich chamam os mesmos commands/queries, e a lógica de negócio não depende de nenhuma das duas interfaces.
- `infrastructure/` é a única camada autorizada a chamar `nft`, `iptables`, `fail2ban-client` e as outras ferramentas externas (subprocess, pty, arquivos).
- `interfaces/` não deve chamar `subprocess` diretamente.
- `ports/` define os contratos esperados pelos adaptadores.
- `core/` fornece o registro de capacidades usado pelas diferentes camadas.
- Os plugins permitem adicionar ou evoluir os backends sem modificar o domínio de negócio.
- A interface Textual (`interfaces/tui/`) apoia-se no [`omega-lib`](https://github.com/) (dependência compartilhada por toda a suíte OMEGA: tema de 9 tokens, detecção de terminal, contratos de port comuns), não publicado no PyPI — incluído no arquivo distribuível (`vendor/omega-lib/`, veja [Instalação](#instalação)).
- Toda chamada potencialmente lenta (backend de firewall, `fail2ban-client`, disco) disparada a partir de uma tela Textual é executada em segundo plano (thread), nunca na thread principal da interface — um dashboard ou um formulário continua responsivo durante a operação em vez de congelar todo o aplicativo.

### Estrutura dos dados

O Omega-Fire usa SQLite via a biblioteca padrão `sqlite3`, sem ORM externo. Os principais conjuntos de dados dizem respeito aos bans, regras, eventos de auditoria e snapshots.

As migrações são versionadas e aplicadas automaticamente na inicialização.

---

## Pré-requisitos

### Sistema

- Linux, prioritariamente Arch Linux e distribuições compatíveis.
- Python 3.10 ou superior.
- Privilégios de root disponíveis via `sudo`.
- Um gerenciador de serviços: systemd, runit ou OpenRC.
- Pelo menos um backend de firewall: nftables ou iptables.
- Um terminal de pelo menos 80x24 (veja [Temas e terminais](#temas-e-terminais) para o detalhe dos perfis de renderização conforme o tamanho disponível).

### Dependências Python

As dependências de produção estão definidas em `requirements.txt`:

- `textual` — interface TUI padrão.
- `omega-lib` — tema, detecção de terminal e contratos compartilhados com a suíte OMEGA (não publicado no PyPI, veja [Arquitetura](#arquitetura) e [Instalação](#instalação)).
- `rich` — renderização da interface `--legacy-cli` e de alguns relatórios.
- `psutil` — informações do sistema (CPU, memória, rede, processos) para o dashboard e os diagnósticos.
- `jinja2` — geração das exportações HTML.
- `python-dotenv` — variáveis de ambiente.
- `pyte` — emulador de terminal virtual, para o encapsulamento do `lnav` (menu 8.6 e visualizador lnav de 5.2 / 5.3).

As ferramentas de qualidade (`pytest`, `black`, `flake8`, `mypy`) estão listadas como comentário em `requirements.txt`: descomente-as ou instale-as separadamente se você contribuir com o projeto (veja [Testes e qualidade](#testes-e-qualidade)).

### Ferramentas opcionais recomendadas

O aplicativo funciona em modo degradado se essas ferramentas estiverem ausentes:

- `fail2ban` — banimento automatizado.
- `conntrack` ou `conntrack-tools` — conexões ativas e estatísticas de rede.
- `lnav` — análise avançada e de vários arquivos de log.

No Arch Linux e derivados:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Instalação

O arquivo oficial é fornecido no formato `.tar.gz`. Verifique sua integridade antes da instalação:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Estes três métodos servem para uma primeira instalação.** Se `~/omega-fire` já existir (atualização de uma versão anterior), use a seção [Atualização](#atualização) abaixo — nunca execute novamente estes comandos de dentro de uma pasta `omega-fire` existente: o `tar` tentaria criar um `omega-fire/omega-fire/` aninhado e falharia com erros de permissão se essa pasta pertencer ao root (frequente se uma extração anterior tiver sido feita por engano com `sudo tar`).

### Método 1 — script de instalação

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Você parece já estar em uma pasta omega-fire — veja a seção Atualização do README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Já extraído aqui, etapa ignorada." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire já existe, movimentação ignorada." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Inicialização:

```bash
./omega-fire.sh
```

Se o alias tiver sido instalado, abra um novo terminal e use:

```bash
fire
```

### Método 2 — instalação completa resiliente

Este comando pode ser executado novamente: ele ignora as etapas já realizadas.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Você parece já estar em uma pasta omega-fire — veja a seção Atualização do README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire já existe, extração ignorada." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv já existe, etapa ignorada." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Grupo omega-fire já existente." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER já é membro do grupo omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Omega-Fire instalado. Execute ./omega-fire.sh."
```

### Método 3 — instalação detalhada

```bash
# 0. Verificar que não se está executando de dentro de um omega-fire existente
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Você parece já estar em uma pasta omega-fire — veja a seção Atualização do README." >&2; exit 1; }

# 1. Extrair
[ -d omega-fire ] && echo "ℹ️ Já extraído aqui, etapa ignorada." || tar -xzf omega-fire.tar.gz

# 2. Mover para o home
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire já existe, movimentação ignorada." || mv omega-fire ~/

# 3. Entrar no projeto
cd ~/omega-fire/

# 4. Criar o ambiente virtual
[ -d .venv ] && echo "ℹ️ .venv já existe, criação ignorada." || python3 -m venv .venv

# 5. Instalar as dependências (omega-lib incluído, se presente, antes do requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Tornar o lançador executável
chmod +x omega-fire.sh

# 7. Preparar var/ para o root e o usuário atual
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Iniciar
./omega-fire.sh
```

`vendor/omega-lib/` só está presente no arquivo oficial (o `build-release.sh` o inclui automaticamente, pois o omega-lib não é publicado no PyPI); em um clone de desenvolvimento, instale-o separadamente a partir de seu próprio repositório (`pip install -e caminho/para/omega-lib`).

O grupo dedicado e o bit `setgid` permitem que o root e o usuário compartilhem os arquivos produzidos em `var/` sem abrir as permissões para todo o sistema. Uma nova sessão ou `newgrp omega-fire` pode ser necessária para se beneficiar imediatamente da participação no grupo.

### Atualização

Se `~/omega-fire` já existir (instalação anterior), **nunca execute novamente os comandos de instalação de dentro dessa pasta**: o `tar` tentaria criar um `omega-fire/omega-fire/` aninhado e falharia, geralmente com uma cascata de erros « Permissão negada » se a pasta pertencer ao `root` (caso frequente se uma extração anterior tiver sido feita por engano com `sudo tar`).

Procedimento recomendado, a partir de qualquer pasta **que não seja `~/omega-fire`** (normalmente o próprio `~`):

```bash
# 1. Verificar o estado e o proprietário da instalação existente
ls -ld ~/omega-fire

# 2. Pôr a instalação antiga de lado em vez de sobrescrevê-la
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Extrair o novo arquivo diretamente no home
tar -xzf omega-fire.tar.gz -C ~/

# 4. Reinstalar (recria o venv, reinstala as dependências, refaz as permissões de var/)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Iniciar
./omega-fire.sh
```

A etapa 4 (`./install.sh`) detecta automaticamente esse caso (banco de dados `var/db/` ausente aqui, pasta `~/omega-fire.old-AAAAMMDD` encontrada logo ao lado) e **recupera por si só** `config/omega-fire.conf`, o banco de dados, a blocklist, os backups, as exportações e as capturas de tela da instalação antiga — sem perguntas, sem etapa manual. Não há nada a fazer além dos pontos 1 a 5 acima, seja qual for o conteúdo da sua instalação anterior.

Se várias pastas parecidas com uma instalação antiga estiverem ao lado (ambíguo), o `install.sh` não adivinha nada: ele exibe os caminhos e convida você a executar `sudo ./migrate-state.sh <pasta>` por conta própria depois de identificar a fonte correta.

Depois de validar a nova instalação, a pasta antiga `~/omega-fire.old-AAAAMMDD` pode ser removida (`sudo rm -rf ~/omega-fire.old-AAAAMMDD`).

### Alias Bash ou Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Em seguida, recarregue o shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Ícones e símbolos Nerd Fonts

Se os ícones não estiverem disponíveis, instale os símbolos Nerd Fonts:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Uso

### Inicialização

```bash
cd ~/omega-fire
./omega-fire.sh

# ou simplesmente, se o alias tiver sido criado:
fire
```

O lançador:

1. Verifica os privilégios de root e reexecuta via `sudo` se necessário.
2. Detecta `.venv`, `venv` ou o Python do sistema.
3. Configura o `PYTHONPATH` para `src/`.
4. Executa `python -m omega_fire` — a interface **Textual**, por padrão.

Para iniciar a antiga interface Rich (digitação sequencial de números) em seu lugar:

```bash
./omega-fire.sh --legacy-cli
```

A interface antiga continua sendo a da versão 3.0, em francês: menu 5 original (sem Biblioteca, Favoritos nem visualizador Clássico), sem "Ver todas as exportações", sem guia de ajuda nem FAQ, sem presets. A interface Textual traz a versão 3.5 completa.

### Idiomas da interface

17 idiomas: francês, inglês, espanhol, português (Brasil), italiano, alemão, neerlandês, polonês, russo, chinês, vietnamita, tailandês, indonésio, japonês, coreano, hindi, árabe. Escolha nas configurações (tecla `s`, « Langue / Language », rótulo que nunca é traduzido), aplicada reiniciando apenas a interface, ou pontualmente com `OMEGA_FIRE_LANG=pt_BR ./omega-fire.sh` (mantido através do `sudo` pelo lançador). No console de texto do Linux (TTY), os idiomas cuja escrita não existe nas fontes de console (vietnamita, chinês, tailandês, japonês, coreano, hindi, árabe) aparecem em inglês durante a sessão. O árabe é exibido da direita para a esquerda. Em hindi, Terminator, GNOME Terminal, Xfce Terminal e Alacritty exibem o texto alinhado; os terminais que compõem eles mesmos as letras ligadas (Kitty, Ghostty, Konsole) podem deslocar quadros e colunas. O **idioma das exportações** (relatórios HTML e TXT) é configurado à parte, « Como a interface » por padrão. O registro do aplicativo e o histórico de auditoria continuam gravados em francês; os títulos do histórico aparecem no idioma escolhido. A interface antiga (`--legacy-cli`) permanece em francês.

### Percurso geral

1. Tela de abertura (splash), depois um aviso se o terminal for pequeno demais.
2. Detecção das capacidades do sistema (tela dedicada, não bloqueante).
3. Menu principal: 8 seções temáticas (1-8), as configurações (9) e a ajuda (10).
4. Seleção de uma seção, depois de uma ação — cada ação abre um formulário cujos campos obrigatórios são todos validados antes de continuar.
5. Confirmação explícita antes de qualquer operação sensível ou destrutiva (flush, purga, restauração...).
6. Execução em segundo plano para as operações lentas (a interface continua utilizável durante a espera), depois retorno ao menu com um resumo do resultado.

### Navegação

- Setas para cima/baixo: mover o cursor em uma lista ou menu.
- Tab / Shift+Tab: navegar entre os campos de um formulário.
- Enter: selecionar ou validar.
- Clicar em uma linha de uma tabela: selecioná-la e preencher previamente os campos correspondentes (fonte a fixar, jail alvo etc.).
- `Esc`: voltar à tela anterior (pede confirmação de saída a partir da tela inicial).
- `a`: ajuda contextual — detalha a ação em curso, ou todas as ações da seção atual se nenhuma tela de ação estiver aberta ainda; o guia completo e a FAQ estão no menu 10.
- `t`: passar para o próximo tema, sem confirmação.
- `r`: detectar novamente o tamanho e a família do terminal.
- `s`: abrir as configurações (tema, perfil de renderização, idiomas, pastas).
- `q` / `Ctrl+Q`: sair, com confirmação.

#### Particularidades da tela lnav (8.6, e visualizador lnav de 5.2 / 5.3)

O `lnav` é encapsulado em um pseudoterminal com um header/footer persistentes do Omega-Fire em torno de sua própria visão, para evitar qualquer colisão entre seus atalhos nativos e os do Omega-Fire:

- Setas ↑↓: navegar nos logs (atalho nativo do `lnav`, repassado como está).
- Setas ←→: rolar horizontalmente nas linhas longas (atalho nativo do `lnav`).
- `g` / `G`: ir para o início / o fim (atalho nativo do `lnav`).
- `Ctrl+C`: marcar a linha atual e copiá-la para a área de transferência do sistema (substitui o comando nativo de cópia do `lnav`, que pode travar em alguns sistemas).
- `t` minúsculo: próximo tema, específico desta visão (o `T` maiúsculo continua sendo o atalho nativo do `lnav` para exibir o tempo decorrido entre as linhas).
- `Ctrl+Q`: voltar ao Omega-Fire (fecha o `lnav` corretamente, sem sair do aplicativo).

---

## Temas e terminais

Dez temas `omega-*` são compartilhados com o resto da suíte OMEGA:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Alterne entre os temas com `t`, ou escolha um diretamente nas configurações (`s`).
- O tema escolhido é persistido e recuperado na próxima execução.
- O Omega-Fire adapta automaticamente a complexidade visual (bordas, splash, densidade de informação) ao terminal detectado por meio de um **perfil de renderização**: Completo, Padrão, Reduzido ou Mono (somente ASCII). O perfil pode ser substituído manualmente nas configurações.

| Tamanho mínimo | Perfil | Terminais típicos |
|---|---|---|
| 120×32 ou mais | Completo | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 ou mais | Padrão | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 ou mais | Reduzido | urxvt, xterm, SSH moderno |
| abaixo de 80×24 | Mono (somente ASCII) | Linux TTY, SSH antigo |

Abaixo de 80×24, a inicialização é recusada (tamanho mínimo exigido); redimensione o terminal e reinicie, ou use `r` após o redimensionamento se a exibição não tiver sido atualizada automaticamente.

---

## Configuração

A configuração específica pode ser ajustada em:

```text
omega-fire/config/omega-fire.conf
```

Ela pode definir, entre outros:

- caminhos dos logs;
- servidores e fontes de monitoramento;
- backends disponíveis ou caminhos personalizados;
- ambientes a analisar;
- parâmetros adaptados a uma instalação específica.

A configuração é relida na reinicialização ou durante uma nova varredura manual (menu 1.3 ou 7.4).

Este arquivo é totalmente opcional (o aplicativo funciona normalmente sem ele, recorrendo às variáveis de ambiente) e **excluído do arquivo distribuível** — uma atualização nunca o sobrescreve silenciosamente, e o `install.sh` o recupera sozinho automaticamente de uma instalação antiga, se for o caso (veja « Atualização » acima).

### Caminhos internos e caminhos do sistema

Por padrão, o Omega-Fire trabalha em sua própria pasta:

```text
var/exports/       # pasta interna do projeto
/var/exports/      # caminho absoluto do sistema
```

A `/` inicial é, portanto, significativa. As importações e exportações para o sistema devem ser solicitadas explicitamente pelo usuário.

---

## Backends e compatibilidade

O Omega-Fire detecta os componentes e ativa apenas as funcionalidades utilizáveis.

| Componente | Função | Status |
|---|---|---|
| nftables | Firewall IPv4/IPv6 moderno | Recomendado |
| iptables | Firewall IPv4 | Compatível |
| ip6tables | Firewall IPv6 com iptables | Compatível se disponível |
| Fail2Ban | Jails e banimentos automatizados | Opcional |
| conntrack | Conexões ativas | Opcional |
| lnav | Análise avançada dos logs | Opcional |
| systemd, runit, OpenRC | Gerenciamento dos serviços | Detecção automática |
| Docker, VNC, servidores | Aplicativos e serviços detectados | Conforme a instalação |

### IPv4 e IPv6

As duas famílias de endereços são suportadas pelos backends compatíveis:

- nftables: IPv4 e IPv6 em dual stack;
- iptables/ip6tables: conforme os binários disponíveis;
- Fail2Ban: conforme a configuração do jail e do sistema.

Os formatos IPv6 longos, compactados, locais, mistos, com zeros e em notação CIDR são tratados pelos componentes correspondentes.

---

## Persistência, logs e exportações

### Persistência

- SQLite via `sqlite3`.
- Tabelas relativas aos bans, regras, auditorias e snapshots.
- Migrações versionadas aplicadas automaticamente.
- Arquivos de estado completo no formato `.tar.gz`.
- Fixados (fontes de log favoritas) e histórico recente persistidos em JSON (`var/runtime/`), sobrevivem a uma reinicialização.

### Logs

- Log de texto do aplicativo: `var/logs/app.log`.
- Log de auditoria JSON estruturado com, entre outros, `event_type`, `actor`, `action`, `result` e `details`.

### Exportações

As exportações estão disponíveis em JSON, TXT e HTML, com vários temas CSS para os relatórios HTML.

---

## Segurança

O Omega-Fire atua sobre componentes críticos do sistema e deve ser usado com cautela.

- A inicialização exige privilégios de root via `sudo`.
- O flush, a purga geral e a aplicação de uma política podem ser destrutivos.
- Uma política predefinida dispara um backup automático antes da modificação.
- No iptables / ip6tables, aplicar uma política ou esvaziar um backend também apaga as regras de outras ferramentas (UFW…): o Omega-Fire avisa e deixa escolher antes de agir.
- Faça um backup manual antes de cada mudança importante.
- Verifique o estado real do firewall, dos jails e das conexões após cada operação.
- Teste primeiro em uma máquina ou um alvo descartável.
- Use as redes de documentação da RFC 5737 para os testes IPv4: `192.0.2.0/24`, `198.51.100.0/24` e `203.0.113.0/24`.
- Verifique as exportações e os snapshots antes de restaurá-los em uma máquina de produção.
- Não conceda permissões mais amplas do que o necessário à pasta `var/`.

---

## Testes e qualidade

A suíte tem 137 testes unitários (mais de 8.000 casos verificados): domínio de negócio, orquestração (`application/`), infraestrutura, e as telas Textual adicionadas ou corrigidas na 3.5, executadas com as folhas de estilo reais (layout, fluxos completos, idiomas das exportações). Este arquivo não contém a pasta `tests/`: obtenha-a no seu repositório de desenvolvimento se precisar executá-la.

```bash
source .venv/bin/activate
python -m unittest discover -s tests/unit -t .
```

A arquitetura em camadas separa estritamente o domínio de negócio da apresentação (`domain/`, `application/`, `ports/` como `Protocol`, veja [Arquitetura](#arquitetura)): a maioria dos testes não precisa de root nem de um firewall real.

Se você contribuir com o projeto, instale as ferramentas de qualidade declaradas (como comentário) em `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Ferramentas disponíveis depois de instaladas:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Estado do projeto

### Pontos operacionais

- TUI Textual unificada para os principais mecanismos de segurança de rede, formulários validados, temas e ajuda contextual compartilhados com a suíte OMEGA.
- Interface Rich histórica mantida como alternativa (`--legacy-cli`).
- Detecção automática das capacidades.
- Gerenciamento dos backends disponíveis.
- Suporte a IPv4/IPv6 conforme as ferramentas presentes.
- Log do aplicativo e auditoria.
- Backup e restauração.
- Exportações JSON, TXT e HTML.
- Dashboard e estatísticas, atualizados em segundo plano sem bloquear a interface.
- Arquitetura em camadas documentada.

### Limitações conhecidas

- A suíte de testes cobre as telas Textual da 3.5, ainda não o conjunto das telas mais antigas (veja [Testes e qualidade](#testes-e-qualidade)).
- O mecanismo `ExecutionPlan`/`PipelineStep` continua parcialmente presente no projeto.
- A disponibilidade exata das funcionalidades depende dos binários, serviços, permissões e configurações da máquina hospedeira.
- A interface Rich histórica (`--legacy-cli`) não é mais o eixo de desenvolvimento ativo; ela é mantida enquanto a interface Textual é totalmente consolidada em condições reais.

---

## Desinstalação

Se os dados permaneceram na pasta do projeto:

```bash
sudo rm -rf ~/omega-fire
```

Remova manualmente os arquivos exportados em outros locais, os eventuais aliases `fire` adicionados em `~/.bashrc` ou `~/.zshrc`, bem como o grupo dedicado se ele não for mais usado:

```bash
sudo groupdel omega-fire
```

Execute este último comando somente se nenhum outro arquivo ou serviço depender desse grupo.

---

## Licença

O Omega-Fire é distribuído sob a licença **MIT**. Consulte o arquivo [`LICENSE`](../../../LICENSE) para o texto completo.

---

> **Omega-Fire — Observar, pilotar, auditar, proteger.**
>
> Uma interface TUI unificada para nftables, iptables, ip6tables, Fail2Ban, os logs e o monitoramento de rede.
