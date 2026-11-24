# 🖥️ Monitor de Promoções de Hardware

> Projeto de um site para acompanhar ofertas de peças de computador, consultar o histórico de preços e acessar os produtos por links de afiliado. A coleta atual é da KaBuM!; a integração com a Terabyte está em processo, adiada até a definição de acesso autorizado.

**Status:** MVP 1 em desenvolvimento. Há coleta individual e por categoria da KaBuM!, persistência com SQLAlchemy, histórico de preços (S2-3), tratamento de indisponibilidade (S2-4), conversor de links de afiliado com ID de teste (S2-5), logs e arquivos de agendamento (S2-6), listagem web e testes. As implementações foram validadas offline; a validação integrada no Oracle permanece pendente. O agendamento foi preparado desabilitado e ainda não foi registrado ou ativado. A integração com a Terabyte (S2-2) permanece em processo, adiada até definir acesso autorizado; seus arquivos experimentais foram removidos.

## 📋 Sobre o projeto

A proposta é reunir promoções de hardware em um só lugar e oferecer histórico de preços para ajudar a avaliar os descontos. A coleta cobre placas de vídeo, SSDs, memórias RAM, processadores, fontes de alimentação, air coolers, water coolers, gabinetes, HDs e placas-mãe.

O MVP 1 será executado localmente, com coleta agendada a cada 15 minutos, armazenamento em Oracle XE e exibição em um painel PHP. Ofertas indisponíveis deixarão de aparecer na listagem, mantendo o histórico registrado.

### Ajustes e melhorias

- [x] Definir os requisitos e o escopo dos MVPs.
- [x] Organizar o backlog em quatro sprints.
- [x] Preparar o script SQL com tabelas, índices, view e cadastro inicial das lojas.
- [x] Implementar a coleta de produtos da KaBuM! por categoria (S2-1).
- [ ] Integrar a Terabyte (S2-2 em processo; adiada até definir acesso autorizado).
- [x] Registrar o primeiro preço e as mudanças sem duplicar o histórico (S2-3; validado offline).
- [x] Tratar indisponibilidade por esgotamento ou remoção confirmada (S2-4; validado offline).
- [x] Implementar a conversão de links de afiliado da KaBuM! com ID de teste (S2-5; validado offline).
- [x] Implementar eventos de coleta e preparar agendamento de 15 minutos (S2-6; validado offline).
- [ ] Validar a coleta integrada no Oracle e autorizar a ativação do agendamento.
- [x] Criar a listagem de promoções com filtro por categoria e ordenação por desconto (S3-1; validação com dados reais no Oracle pendente).
- [x] Criar a página do produto com gráfico de histórico de preços (S3-2; validação visual pendente).
- [x] Implementar login do painel administrativo (S3-3).
- [x] Implementar painel de monitoramento da coleta (S3-4).
- [ ] Automatizar os testes e validar três dias de operação local.


## 🛠️ Tecnologias

Stack prevista para o MVP 1:

- **Coleta:** Python, requests, BeautifulSoup e Playwright.
- **Banco de dados:** Oracle XE 18c+ e SQLAlchemy.
- **Interface:** PHP com PDO e Chart.js.
- **Testes:** pytest.

```text
Agendador → Scraper Python → Oracle XE ← Painel PHP
```

## 💻 Pré-requisitos

Para preparar o banco disponível neste repositório:

- Oracle Database XE 18c ou superior, conforme o script SQL.
- Um cliente SQL compatível com Oracle, como SQL Developer ou SQLcl.
- Um usuário de desenvolvimento com permissão para criar tabelas, índices e views.

Para as próximas etapas, também serão necessários Python, PHP com suporte a PDO para Oracle e as dependências da coleta. As versões e os comandos de instalação serão documentados junto à implementação.

Antes de começar, consulte o [PRD](docs/PRD%20-%20Monitor%20de%20Promo%C3%A7%C3%B5es%20de%20Hardware.pdf) e o [backlog de sprints](docs/Backlog-Sprints.pdf).

## 🚀 Preparando o projeto

1. Baixe ou clone este repositório e abra sua pasta local.
2. Inicie o Oracle XE e conecte-se ao banco com o usuário de desenvolvimento.
3. Execute o arquivo [01_criar_tabelas.sql](docs/01_criar_tabelas.sql) como script no cliente SQL.

O script cria cinco tabelas e uma view:

| Objeto | Finalidade |
| --- | --- |
| `LOJA` | Cadastro das lojas e configuração dos links de afiliado |
| `PRODUTO` | Dados dos produtos, preços e disponibilidade |
| `HISTORICO_PRECO` | Registros de preço associados aos produtos |
| `LOG_COLETA` | Eventos e falhas da coleta |
| `USUARIO` | Credenciais do painel, com armazenamento do hash da senha |
| `V_PROMOCOES_ATIVAS` | Produtos disponíveis com desconto calculado |

Também são inseridos os cadastros iniciais da KaBuM! e da Terabyte. Execute o script em um esquema novo: ele não inclui uma rotina de recriação de objetos existentes.

## ☕ Usando o projeto

Nesta etapa, é possível preparar e consultar a estrutura do banco. Após executar o script, confira as lojas cadastradas:

```sql
SELECT ID, NOME, URL_BASE, ATIVA
FROM LOJA;
```

Para consultar as promoções quando houver produtos cadastrados:

```sql
SELECT NOME, LOJA, CATEGORIA, PRECO_ATUAL, DESCONTO_PCT
FROM V_PROMOCOES_ATIVAS
ORDER BY DESCONTO_PCT DESC;
```

A view ficará vazia até que produtos com desconto sejam inseridos.

### Coleta da KaBuM! — S2-1

Instale as dependências no ambiente virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para conferir a coleta em todas as categorias sem acessar o banco:

```powershell
.\.venv\Scripts\python.exe -m scraper.coletar --categorias GPU SSD RAM CPU FONTE COOLER WATER_COOLER GABINETE HD PLACA_MAE --max-paginas 1 --max-produtos 2 --sem-gravar
```

Para gravar no Oracle, configure `DB_HOST`, `DB_PORT`, `DB_SERVICE_NAME`, `DB_USER` e `DB_PASSWORD` no `.env` da raiz e execute sem `--sem-gravar`:

```powershell
.\.venv\Scripts\python.exe -m scraper.coletar --categorias SSD --max-paginas 2 --max-produtos 30
```

Os limites valem por categoria. O padrão é uma página e até 20 produtos tentados na descoberta, contando falhas. Com persistência, há também uma revisão de até 20 produtos já cadastrados, conforme a seção S2-4 abaixo. O resumo informa coletados, gravados, páginas, falhas e se o limite interrompeu a varredura. Havendo falhas, o comando retorna código 1 e continua os demais produtos e categorias. Uma execução limitada não representa o catálogo completo e não deve ser usada para inferir produtos removidos.

A coleta respeita `robots.txt`, aguarda pelo menos dois segundos entre requisições e reutiliza páginas em memória durante a execução. Imagem e preço original são lidos quando informados; valores ausentes não substituem os já armazenados. Cada produto é gravado em uma transação própria.

O comando individual continua disponível:

```powershell
.\.venv\Scripts\python.exe -m scraper.coletar https://www.kabum.com.br/produto/621162 --categoria SSD
```

### Histórico de preços — S2-3

Os comandos de coleta individual e por categoria agora gravam automaticamente em `HISTORICO_PRECO`, na mesma transação do produto. A tabela já está prevista no script SQL existente; esta implementação não altera a estrutura do banco.

O primeiro preço coletado gera um registro. As próximas coletas só acrescentam um ponto quando o preço atual difere do último registrado, tanto em queda quanto em aumento. Por exemplo, **R$ 100 → R$ 100 → R$ 90** gera dois pontos: **R$ 100 e R$ 90**. Voltar posteriormente a R$ 100 gera outro ponto, pois houve uma nova mudança.

Produtos cadastrados antes dessa implementação, sem histórico, recebem seu primeiro ponto na próxima coleta que informar preço. Não são reconstruídos preços ou datas passados. Preço ausente não gera registro nem apaga o último preço ou o histórico. Mudanças apenas no preço original ou na disponibilidade não criam pontos adicionais.

Cada ponto guarda o preço original conhecido naquele momento. Se esse campo estiver ausente na coleta, usa o valor preservado no produto. Os pontos anteriores permanecem intactos. Se a gravação do histórico falhar, a transação também desfaz a alteração do produto.

**Validação:** 43 testes Python offline aprovados, com SQLite em memória. Nesta etapa não houve coleta online nem gravação no Oracle local. `--sem-gravar` continua sem persistir produtos ou histórico. A exibição do gráfico pertence à sprint 3.

### Indisponibilidade e retorno ao estoque — S2-4

Um produto é marcado como indisponível quando uma coleta válida informar esgotamento ou descontinuação, ou quando a própria URL de produto responder **HTTP 404 ou 410**, sem redirecionamento para outra URL. Um 404 no `robots.txt` ou na categoria não confirma remoção de produto.

Bloqueio 403, erro 503, timeout, falha de rede, HTML inválido e redirecionamento para uma página ausente preservam o estado anterior. A ausência em uma listagem, completa ou limitada, também não é usada como prova de remoção.

Na coleta por categoria **com persistência**, o comando revisa até `--max-produtos` URLs já cadastradas que não foram verificadas na descoberta. Prioriza os produtos com atualização mais antiga e inclui indisponíveis para detectar retorno ao estoque. Essa revisão tem um limite adicional: com `--max-produtos 20`, podem ser tentadas até 20 páginas de produto na descoberta e mais 20 na revisão, por categoria, além das páginas de listagem e `robots.txt`. As requisições continuam respeitando intervalo e cache.

O resumo inclui `revisados`, `removidos` (404/410 confirmados) e `marcados_indisponiveis` (remoções aplicadas a produtos existentes). Os itens esgotados com HTML válido entram em `coletados` e `gravados`. `--sem-gravar` não consulta os cadastrados nem aplica alterações; apenas informa os resultados obtidos na descoberta.

Uma remoção confirmada altera a disponibilidade e a data de atualização do produto existente, preservando nome, URLs, preços, última data em que foi visto e histórico. Não cria cadastro para URL removida desconhecida. Em item esgotado, preço ausente ou zero não substitui o último preço conhecido. Uma coleta válida posterior com estoque reativa o produto; preço igual não duplica o histórico.

A API `/api/produtos.php` agora lista somente produtos disponíveis de lojas ativas. Se todos estiverem indisponíveis, a interface mostra “Nenhum produto disponível”. Os registros continuam no banco. O comando individual existente também permite verificar uma URL cadastrada e aplicar uma remoção confirmada.

**Validação:** 55 testes Python offline, 3 testes da interface e verificação de sintaxe PHP aprovados. Nenhuma coleta online nem gravação no Oracle local foi executada nesta etapa. O agendamento automático e os logs permanecem na S2-6.

### Links de afiliado KaBuM! — S2-5

O conversor isolado em `scraper/afiliados.py` recebe a URL original de um produto da KaBuM! e gera um deeplink Awin. O programa utiliza a Awin, com anunciante `17729`, conforme a [página oficial KaBuM!](https://www.kabum.com.br/hotsite/afiliados/) e o [perfil do anunciante](https://ui.awin.com/merchant-profile/17729). O formato usa `https://www.awin1.com/cread.php` com `awinmid`, `awinaffid` e `ued` (URL original codificada).

Enquanto não houver aprovação, o projeto usa **ID `0` como placeholder local**. Esse valor não é um ID de sandbox oficial da Awin. Ele serve para testar a montagem, o armazenamento e o uso do link; não comprova redirecionamento, rastreamento ou comissão. Os testes não abrem links de afiliado nem fazem requisições à Awin.

A configuração opcional no `.env` da raiz é:

```dotenv
KABUM_AFILIADO_ID=0
```

Sem essa variável, o padrão também é `0`. Uma variável do processo tem prioridade sobre o `.env`. O conversor aceita apenas IDs numéricos não negativos em texto, com até 20 dígitos. Valor vazio ou inválido interrompe a gravação do produto, em vez de montar um link incorreto. Após a aprovação, será necessário configurar o ID real e confirmar os links no programa da Awin.

Em cada gravação válida de produto, `URL_AFILIADO` é gerada ou atualizada, enquanto `URL_ORIGINAL` continua sendo a URL de coleta. Alterar apenas o ID não cria ponto de histórico de preço. Nenhum cadastro existente é atualizado automaticamente ao editar o `.env`: os novos links serão persistidos na próxima coleta/revisão que gravar o produto. Uma confirmação de remoção por 404/410 preserva o link já armazenado.

A API fornece `url_afiliado`, e o botão “Ver na loja” usa esse link quando válido. A interface confere domínio e caminho da Awin, anunciante, ID e destino correspondente ao mesmo produto da KaBuM!. Links ausentes ou inválidos usam a URL original segura como alternativa; links de outras lojas não são aceitos nesta etapa. O link afiliado recebe `rel="sponsored noopener noreferrer"`.

**Validação:** 63 testes Python offline, 5 testes da interface e sintaxe PHP aprovados. Não houve coleta online, acesso a links Awin, atualização de produtos antigos ou gravação no Oracle local. A validação de navegação e atribuição reais depende de conta aprovada e ID válido.

### Logs e agendamento — S2-6

A coleta registra eventos em `LOG_COLETA`: `PRODUTO_NOVO`, `PRECO_ALTERADO`, `ESGOTADO`, `VOLTOU_ESTOQUE`, `COLETA_OK` e `COLETA_FALHA`. As mudanças do produto e seus eventos são gravados na mesma transação. Recoletas sem mudança não repetem eventos de preço/estoque; os resultados de coleta são registrados por execução individual ou categoria. Falhas de produtos conhecidos podem ser associadas ao seu cadastro.

Falhas são registradas em uma transação separada, depois do rollback da operação que falhou. As mensagens do banco são fixas, sem conteúdo bruto de exceções, SQL, URLs ou credenciais. Se o banco não aceitar o registro, o comando retorna falha e usa `logs/coleta.log` como apoio local. Esse arquivo também recebe o resultado geral da entrada agendada, com horário UTC−04:00 (Manaus), rotação de 1 MiB e até três cópias. Os logs locais são ignorados pelo Git; se o disco também falhar, sua gravação não é garantida.

A trava `.coleta.lock` impede simultaneidade entre comandos individuais, lotes e a entrada agendada neste mesmo projeto. Ela é liberada pelo sistema ao encerrar o processo; o arquivo permanece e sua presença, sozinha, não significa coleta ativa. Não apague o arquivo enquanto houver coleta em execução. Códigos de saída: `0` para conclusão sem falhas, `1` para falha e `2` para execução ignorada por outra coleta em andamento.

**A S4-5 usa uma tarefa temporária de 72 horas.** A configuração permanente pode ser preparada em XML, sem registrar tarefa nem executar coleta:

```powershell
.\scripts\preparar_agendamento.ps1
```

O script gera `logs/coleta-kabum.xml`, ignorado pelo Git, com:

- Repetição a cada 15 minutos, sem prazo final, a partir do horário definido no XML.
- Estado desabilitado (`Enabled=false`) e política `IgnoreNew`: se uma execução durar mais de 15 minutos, outra não começa em paralelo.
- Python `pythonw.exe` da `.venv`, módulo `scraper.agendado`, diretório do projeto e usuário atual, sem senha ou credenciais de banco no XML.
- Execução na sessão do usuário conectado, com limite de 30 minutos por coleta. Por padrão, exige alimentação externa. Use `-PermitirBateria` para executar na bateria e `-AcordarComputador` para solicitar que o Windows acorde da suspensão, quando os temporizadores de ativação estiverem disponíveis.

A entrada agendada coleta as categorias configuradas em `scraper/categorias.py` com uma página e até 20 produtos de descoberta, mais até 20 revisões de cadastrados por categoria. O log registra o início e o desfecho de cada tentativa agendada. Uma falha de DNS recebe uma nova tentativa após pelo menos cinco segundos. Se persistir, o lote pausa as requisições à KaBuM! por 30 segundos e preserva os dados das consultas que falharam. **Executar `python -m scraper.agendado` realiza coleta e gravação reais.**

O XML foi aceito pela interface COM do Agendador, sem registro de tarefa. A importação, a ativação e a primeira coleta real dependem de autorização separada, conforme combinado. O Windows, a sessão do usuário, o Oracle e o listener precisam estar disponíveis. Ao ativar posteriormente, `StartWhenAvailable` pode executar uma ocorrência já vencida.

**Validação:** 75 testes Python offline aprovados, incluindo eventos, rollback, apoio quando o banco falha, liberação da trava e bloqueio de outro processo. Nenhuma tarefa foi registrada/ativada e nenhum dado foi gravado no Oracle. O painel de monitoramento continua previsto para a sprint 3; a operação estável por três dias continua prevista para a sprint 4.

### Terabyte — S2-2 em processo (adiada)

A integração está em processo, mas foi deixada de lado nesta etapa por decisão do responsável. Nas tentativas de 17/11/2026, a proteção Cloudflare retornou **HTTP 403**, inclusive no acesso ao `robots.txt`, e o navegador automatizado recebeu um desafio de acesso. Isso impediu a coleta e a validação do HTML real dos produtos.

Além do bloqueio técnico, as [regras oficiais do programa de parceiros](https://www.terabyteshop.com.br/site/regras-programa-de-parceiros), consultadas nessa data, proíbem o uso de recursos automatizados para coletar informações. A participação no programa de afiliados, por si só, não assegura autorização para essa coleta.

A retomada depende de definir com a Terabyte uma forma autorizada de acesso aos produtos, como uma API, um catálogo fornecido pela loja ou uma permissão específica de coleta. Essas alternativas ainda não foram confirmadas com a empresa; nenhum contato foi enviado pelo projeto nesta etapa.

O módulo experimental, os testes e as fixtures da Terabyte foram removidos, assim como a opção `--loja`. A coleta disponível segue com a KaBuM!, pelos comandos acima. A S2-2 não é considerada concluída.

### Home de promoções — S3-1

Inicie o servidor de desenvolvimento com `php -S 127.0.0.1:8080 -t web app/roteador.php` e abra `http://127.0.0.1:8080`. A home consulta `V_PROMOCOES_ATIVAS` no Oracle, exibe preço atual, preço original e desconto, e mostra até 100 ofertas em ordem de maior desconto. O filtro de categoria é aplicado no banco antes desse limite. O roteador aceita tanto `/api/produtos` quanto `/api/produtos.php`.

### Página do produto — S3-2

Na home, clique no nome da oferta para abrir `/produto.html?id=<id>`. A página mostra o preço, a disponibilidade na última coleta e o botão **Ver na loja**. Quando houver registros, o histórico aparece em um gráfico Chart.js e em uma tabela de datas e preços.

### Login do painel — S3-3

No PowerShell, cadastre o administrador com `.\scripts\criar_admin.ps1 -Email "seu-email@exemplo.com"`. Digite e confirme a senha no prompt oculto. Use pelo menos 8 caracteres. O comando exige o PHP com suporte a Argon2id e acesso ao Oracle configurado.

Abra `http://127.0.0.1:8080/login` com o servidor local em execução. Use HTTPS para acesso fora do loopback. O painel encerra a sessão após 30 minutos de inatividade e limita o login a 10 tentativas por endereço em cinco minutos.

### Monitoramento da coleta — S3-4

Depois do login, `/painel` mostra o resultado da última tentativa registrada por loja e até 20 eventos, do mais recente para o mais antigo. O status usa os eventos de conclusão ou falha da coleta. A lista inclui mudanças de preço, estoque e novos produtos.

### Testes offline

Para executar os testes offline, incluindo o CT-01:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

O CT-01 usa `php`, `php-cgi` com PDO_SQLITE e Argon2id, e `node` no PATH. Para rodar só esse cenário, acrescente `tests/test_ct01.py` ao comando do pytest.

### Estrutura do repositório

```text
proj-promo/
├── docs/
│   ├── 01_criar_tabelas.sql
│   ├── Backlog-Sprints.pdf
│   └── PRD - Monitor de Promoções de Hardware.pdf
├── scraper/    # Reservado para a coleta em Python
├── tests/      # Reservado para testes e fixtures
├── web/        # Reservado para o painel PHP
├── .gitignore
└── README.md
```

### Validação planejada

O **CT-01** automatiza o ciclo de vida de uma promoção da KaBuM!: coleta de fixture, persistência, mudança de preço, exibição, link de afiliado e indisponibilidade. Também verifica a preservação de dados em caso de falha e o acesso ao painel por login.

O teste usa SQLite temporário compartilhado pelo coletor Python e pelo PHP, com um DOM simulado em Node.js. Na S4-4, a primeira oferta foi renderizada em até 1,28 s em cinco medições com celular simulado e uma oferta no Oracle local. A revisão S4-6 aceitou a KaBuM! como única loja da validação e liberou o desenvolvimento do MVP 2. A conferência de 72 horas consecutivas de operação foi transferida para o encerramento do projeto.

## 📫 Contribuindo para o projeto

1. Faça um fork do repositório.
2. Crie uma branch: `git checkout -b feat/minha-contribuicao`.
3. Faça as alterações seguindo o escopo do PRD e do backlog.
4. Valide o comportamento alterado e registre o commit: `git commit -m "Descreve a contribuição"`.
5. Envie a branch: `git push origin feat/minha-contribuicao`.
6. Abra um pull request com a descrição da mudança e da validação realizada.

Mantenha credenciais fora do código. O `.gitignore` já contempla arquivos `.env`, ambientes virtuais, caches e logs locais.

## 📝 Licença

Este repositório ainda não possui um arquivo de licença. A licença de uso e distribuição será definida pelo responsável pelo projeto.

---

Estrutura do README baseada no [modelo de Iuri Silva](https://github.com/iuricode/readme-template/blob/main/repositorio/exemplo-01.md).
### PostgreSQL para o MVP 2

O coletor e o PHP usam Oracle por padrão. Para testar PostgreSQL em um ambiente separado, inicialize um banco vazio com [o esquema PostgreSQL](docs/03_criar_tabelas_postgresql.sql), instale as dependências Python de `requirements.txt` e habilite `pdo_pgsql` no PHP. Configure `DB_DRIVER=postgresql`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD` nos dois processos. As conexões remotas exigem TLS. Em `127.0.0.1`, os clientes preferem TLS e aceitam a conexão local sem certificado. As datas exibidas continuam no horário de Manaus.

O esquema cria as tabelas e a visão de ofertas. A transferência dos dados do Oracle e a validação do CT-01 em PostgreSQL são etapas separadas.

#### Inicializar o banco no servidor (S5-2)

Na validação local no Windows, use `127.0.0.1` como host e a porta configurada durante a instalação. Se o `psql` tentar chamar `cat` ao exibir os resultados, adicione `-P pager=off` ao comando de conferência.

Com o `psql` instalado, use um banco PostgreSQL vazio, o endereço externo do servidor e um usuário com permissão para criar objetos no esquema `public`. Execute a partir da raiz do projeto. O `psql` solicita a senha no terminal.

```powershell
psql -X -W -v ON_ERROR_STOP=1 --dbname 'host=HOST_POSTGRES port=5432 dbname=NOME_DO_BANCO user=USUARIO_POSTGRES sslmode=verify-full' --file docs/03_criar_tabelas_postgresql.sql
```

Para `verify-full`, configure a autoridade certificadora confiável para o servidor no cliente PostgreSQL e use o hostname do certificado. O script usa uma transação para aplicar o esquema inteiro. Em caso de erro, confira a mensagem antes de tentar novamente.

Na mesma conexão, confira as cinco tabelas (`loja`, `produto`, `historico_preco`, `log_coleta` e `usuario`), os índices e a visão. Os cadastros iniciais esperados são Kabum e Terabyte, com zero promoções antes da carga de produtos.

```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
SELECT indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY indexname;
SELECT nome FROM public.loja ORDER BY nome;
SELECT COUNT(*) AS ofertas FROM public.v_promocoes_ativas;
```

### Preparar a publicação na Render (S5-4)

O `Dockerfile` monta o serviço web com Apache, PHP e `pdo_pgsql`, na porta `10000`. A raiz pública é `web/`. A Render termina o HTTPS e fornece o endereço `onrender.com` para a validação inicial.

1. Conecte à Render um repositório Git com estes arquivos e crie um **Web Service** com runtime **Docker**. O `Dockerfile` está na raiz do projeto.
2. Provisione um **PostgreSQL** na mesma região. Inicialize o destino e importe as tabelas da base local preservando os IDs e as sequências. Confira os dados no destino antes de conectar o site.
3. Defina `DB_DRIVER=postgresql`, `DB_HOST` com o hostname interno do banco, `DB_PORT=5432`, `DB_NAME`, `DB_USER` e `DB_PASSWORD` nas variáveis do serviço. Cadastre a senha no painel da Render.
4. Use `/` para verificar se o Apache está respondendo. No endereço HTTPS, confira a home, `GET /api/produtos.php`, um produto com histórico e o redirecionamento de `/painel` para `/login` sem sessão. Faça login e confirme o atributo `Secure` no cookie `promo_painel`.

O banco de produção deve ser provisionado antes da validação da API. O endereço `onrender.com` permite começar a validação enquanto o domínio próprio está pendente. O coletor agendado fica na S5-5.
