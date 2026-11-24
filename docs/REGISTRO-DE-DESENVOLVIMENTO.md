# Registro de desenvolvimento

Este documento registra as atividades realizadas no projeto, as decisões técnicas e as evidências de validação. Cada nova etapa deverá acrescentar o que foi feito, por que foi necessário, como foi executado, para que serve e o que ficou pendente.

O registro inicial foi escrito em **16/11/2026**, com base nas atividades desta sessão. As datas de criação de arquivos anteriores à sessão não foram tratadas como datas de execução das tarefas.

## 1. Organização do README

### O que foi feito

O `README.md`, inicialmente vazio, foi preenchido seguindo a estrutura do [modelo indicado](https://github.com/iuricode/readme-template/blob/main/repositorio/exemplo-01.md). O conteúdo foi adaptado ao PRD, ao backlog e ao script SQL disponíveis em `docs`.

Foram documentados o objetivo do monitor de promoções, o estado atual do repositório, as funcionalidades planejadas, as tecnologias, os pré-requisitos, a preparação do banco, exemplos de consultas e orientações para contribuir. Depois, a seção de tecnologias foi resumida a pedido do responsável pelo projeto.

### Por que

O README é o ponto de entrada para quem abre o repositório. Ele precisa explicar a proposta e permitir que uma pessoa identifique o que já pode utilizar. Como ainda não há scraper nem painel implementados, era necessário distinguir os recursos previstos dos recursos existentes.

### Como

Foram examinados os arquivos e diretórios locais e consultado o modelo fornecido. O PRD foi lido para identificar a arquitetura e os requisitos; o backlog, para entender a sequência de implementação; e o SQL, para conferir os objetos efetivamente definidos.

Para ler o PRD em PDF, foi instalada a biblioteca `pypdf` em um diretório temporário, fora das dependências do projeto. O arquivo `Backlog-Sprints.pdf` apresentou conteúdo interno de documento Word, apesar da extensão `.pdf`; seu texto foi lido diretamente da estrutura XML interna, sem alterar o arquivo original.

Os links locais usados no README foram conferidos. Não foi atribuída uma licença inexistente nem foram inventados comandos para executar uma aplicação ainda não implementada.

### Para que serve

Permite apresentar o projeto, orientar a preparação inicial e acompanhar as entregas previstas. Os detalhes das atividades ficam neste registro para manter o README mais direto.

## 2. S1-1 — Repositório, pastas e arquivos ignorados

### O que foi verificado

Na inspeção, o repositório Git já estava inicializado e os diretórios `docs`, `scraper`, `tests` e `web` já existiam. O `.gitignore` também já estava presente. Esses itens foram inspecionados; sua criação não foi realizada nesta sessão.

Foram encontrados arquivos `.gitkeep` em `scraper` e `tests/fixtures`. Não foi encontrado um arquivo equivalente em `web` durante a verificação.

### Por que

A separação em pastas prepara o projeto para receber código com responsabilidades distintas:

| Pasta | Finalidade |
| --- | --- |
| `docs` | Requisitos, planejamento, scripts SQL e registros técnicos |
| `scraper` | Coleta de informações das lojas em Python |
| `web` | Interface e painel em PHP |
| `tests` | Testes automatizados e dados de teste |
| `tests/fixtures` | Páginas HTML salvas para testes reproduzíveis |

O Git permite acompanhar alterações. O `.gitignore` evita incluir no versionamento arquivos locais, gerados ou sensíveis.

### Como

Foram usados `git rev-parse --is-inside-work-tree`, `git status --short` e uma consulta ao histórico de commits. Também foram listadas as pastas e lidas as regras do `.gitignore`.

As regras existentes ignoram `.env` e suas variações, permitem um eventual `.env.example` e excluem `.venv`, caches Python, caches de testes e logs. Essas regras não removem segredos de arquivos já versionados; por isso, continua sendo necessário conferir o conteúdo antes de um commit.

O `.gitkeep` é um arquivo convencional usado para permitir que uma pasta sem outros arquivos seja registrada no Git. O Git não registra diretórios vazios por si só.

### Resultado e pendências

A estrutura inicial está preparada, mas não havia commits na verificação. O responsável decidiu adiar o commit e prosseguir para a S1-2. Nenhum commit ou envio ao GitHub foi realizado nesta sessão.

Commit e envio são operações diferentes: o commit registra uma versão local; o push envia os commits para um repositório remoto. A definição de pronto do backlog exige versionamento, então essa parte da S1-1 permanece adiada. Também falta garantir a preservação de `web` no Git quando ela ainda estiver vazia.

## 3. S1-2 — Verificação e preparação do Python

### O que foi feito

Foi confirmado que o Python **3.14.0** já estava instalado e acessível pelo terminal. Em seguida, foi criado o ambiente virtual `.venv` na raiz do projeto, com o pip **25.2** disponível dentro dele.

### Por que

O scraper será escrito em Python. Um ambiente virtual isola as bibliotecas do projeto das bibliotecas globais da máquina, reduzindo conflitos com outros projetos e permitindo organizar as dependências posteriormente.

### Como

Foi executado:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip --version
```

A primeira tentativa de criar o ambiente falhou na etapa `ensurepip`, dentro do ambiente restrito de execução. A operação foi repetida com execução autorizada fora dessa restrição e concluída. A validação confirmou que o pip utilizado pertence à `.venv` deste projeto.

### Para que serve

As próximas instalações de dependências Python poderão usar o interpretador do ambiente virtual, sem depender da ativação no terminal:

```powershell
.\.venv\Scripts\python.exe -m pip --version
```

Esse comando apenas verifica o pip. Bibliotecas como SQLAlchemy, Playwright e o driver Python para Oracle ainda não foram instaladas como parte desta etapa. A conexão Python–Oracle também ainda não foi testada.

## 4. S1-2 — Verificação do Oracle XE

### O que foi verificado

Na primeira inspeção não foram encontrados serviços ou uma instalação Oracle registrada. Em uma nova verificação solicitada pelo responsável, o **Oracle Database 21c Express Edition** já estava instalado em `C:\app\mathe\product\21c\`. A instalação do Oracle não foi executada pelo assistente nesta sessão.

Foram confirmados os serviços `OracleServiceXE` e `OracleOraDB21Home1TNSListener` em execução. O listener informou o serviço `xepdb1` no estado `READY`, na porta **1521**.

### Por que

O Oracle XE armazenará os produtos, o histórico de preços, os eventos de coleta e os usuários do painel no MVP 1. A instalação sozinha não garante disponibilidade: a instância precisa estar em execução e o listener deve receber as conexões.

### Como

Os serviços foram consultados no Windows e o listener foi verificado com o executável da instalação:

```powershell
& 'C:\app\mathe\product\21c\dbhomeXE\bin\lsnrctl.exe' status
```

Também foi feita uma consulta administrativa local, somente de leitura, usando SQL*Plus com autenticação do sistema operacional:

```sql
SELECT NAME, OPEN_MODE FROM V$PDBS;
```

O resultado mostrou `XEPDB1` em `READ WRITE`. Isso confirma que o banco plugável destinado à conexão está aberto para leitura e escrita. O estado `READ ONLY` de `PDB$SEED`, também exibido na consulta, corresponde ao banco modelo.

### Para que serve

Essas verificações estabelecem que o banco está disponível para a preparação do esquema da aplicação. O uso administrativo nesta verificação não define o usuário que será utilizado pelo scraper ou pelo painel.

## 5. S1-2 — Configuração do PHP para Oracle

### Situação encontrada

O PHP **8.5.12**, compilação **NTS x64 com VS17**, já estava instalado e executava pelo terminal. Entretanto, não carregava um `php.ini` e a lista de drivers disponíveis no PDO estava vazia.

A instalação utilizada está em:

```text
C:\Users\mathe\Downloads\php-8.5.12-1-nts-Win32-vs17-x64
```

### Por que

O painel será escrito em PHP e acessará o Oracle via PDO. PDO fornece a interface de acesso a dados, mas precisa de um driver específico para cada banco. Para Oracle, esse driver é o `pdo_oci`.

Foi escolhida a extensão compatível com a versão e a compilação do PHP instalado. Essa compatibilidade envolve PHP 8.5, arquitetura x64, modo NTS e compilador VS17. Uma DLL de outra combinação pode não carregar.

### Como

1. Foi consultada a distribuição oficial do [PDO_OCI 1.2.0 para Windows](https://pecl.php.net/package/PDO_OCI/1.2.0/windows).
2. Foi baixado o pacote `php_pdo_oci-1.2.0-8.5-nts-vs17-x64.zip` de `downloads.php.net` e extraído em uma pasta temporária.
3. A DLL `php_pdo_oci.dll` foi copiada para a pasta `ext` do PHP.
4. Como não existia um `php.ini`, ele foi criado a partir do `php.ini-development` distribuído com o PHP.
5. Foram acrescentadas as configurações abaixo, usando o caminho absoluto da instalação para `extension_dir`:

```ini
extension_dir = "C:\Users\mathe\Downloads\php-8.5.12-1-nts-Win32-vs17-x64\ext"
extension = pdo_oci
date.timezone = America/Manaus
```

6. A pasta `C:\app\mathe\product\21c\dbhomeXE\bin` foi acrescentada ao `PATH` do usuário, preservando as entradas anteriores. Ela contém a biblioteca Oracle `oci.dll`, necessária ao driver.

Foi aproveitado o cliente que acompanha a instalação do Oracle, sem instalar um Instant Client separado. O fuso horário foi definido para corresponder ao contexto local do projeto.

### Para que serve

O `php.ini` ativa e configura as extensões do PHP. O `extension_dir` indica onde encontrar as DLLs; `extension = pdo_oci` habilita o acesso ao Oracle; e o `PATH` permite localizar as bibliotecas nativas de que o driver depende.

As alterações no `php.ini` e no `PATH` são configurações da máquina, fora do repositório. Novos terminais recebem o `PATH` atualizado; terminais e IDEs já abertos podem precisar ser reiniciados. Se a pasta do PHP for movida, seus caminhos deverão ser revistos.

## 6. S1-2 — Validação da comunicação PHP–Oracle

### Como foi validado

Foram executadas as verificações:

```powershell
php --ini
php -r "echo implode(', ', PDO::getAvailableDrivers()), PHP_EOL;"
```

O PHP confirmou o carregamento do novo `php.ini`, e a lista de drivers passou a incluir `oci`.

Em seguida, foi tentada uma conexão PDO ao serviço `xepdb1`, no endereço informado pelo listener, com um nome de usuário e uma senha fictícios criados apenas para a verificação. O Oracle respondeu com **ORA-01017**, indicando rejeição das credenciais.

### Por que usar credenciais fictícias

Esse teste permite verificar se o driver carrega, alcança o serviço e recebe uma resposta do banco sem solicitar ou registrar uma senha administrativa. A rejeição era o resultado esperado para aquelas credenciais.

### O que o resultado comprova

Comprova a comunicação entre o PHP/PDO_OCI e o serviço Oracle. **Não comprova uma sessão autenticada da aplicação, permissões sobre tabelas ou execução de consultas pelo PHP.** Esses testes dependem da preparação do usuário e do esquema da aplicação.

A tentativa inicial dentro do ambiente restrito retornou erros de autenticação e permissão (`ORA-12638` no PDO e `ORA-12546` no SQL*Plus). As verificações foram repetidas com execução autorizada fora da restrição. Nesse contexto, o PDO recebeu a rejeição esperada das credenciais fictícias e o SQL*Plus conseguiu consultar o estado do banco. Não foi necessário alterar a configuração de autenticação do Oracle.

## 7. Estado ao final da preparação

| Item | Resultado |
| --- | --- |
| README | Criado e adaptado ao projeto; tecnologias resumidas |
| S1-1 | Estrutura verificada; commit adiado por decisão do responsável |
| Python | Versão 3.14.0 disponível |
| Ambiente virtual | `.venv` criada, com pip 25.2 |
| Oracle XE | Versão 21c instalada, instância e listener ativos |
| Banco plugável | `XEPDB1` aberto em `READ WRITE` |
| PHP | Versão 8.5.12 executando com `php.ini` carregado |
| PDO Oracle | Driver `oci` ativo e comunicação com `xepdb1` verificada |
| S1-2 | Preparação do ambiente concluída, com os limites de validação descritos acima |

A configuração e o uso de um usuário próprio da aplicação, a execução de `01_criar_tabelas.sql` e as consultas autenticadas da aplicação ainda não foram realizados nesta sessão. O script SQL já existia no repositório; sua presença não significa que as tabelas tenham sido criadas no banco.

## 8. Próxima etapa prevista — S1-3

A S1-3 consiste em criar as tabelas com o script SQL existente. Antes da execução, será necessário definir e validar o usuário e o esquema de desenvolvimento no `XEPDB1`. Depois, deverão ser conferidos os objetos criados e os cadastros iniciais das lojas.

Essa etapa permitirá que o scraper grave os dados coletados e que o painel os consulte. A criação deste registro não executa a S1-3.

## 9. Como manter este registro

As próximas atividades deverão acrescentar entradas com a seguinte estrutura, sem registrar senhas ou outros segredos:

```text
Data e tarefa:
O que foi feito:
Por que foi necessário:
Como foi executado:
Para que serve:
Como foi validado e qual foi o resultado:
Limitações e pendências:
```

As entradas devem distinguir ações executadas, situações apenas observadas e decisões ainda planejadas. Quando uma configuração mudar, a nova entrada deverá explicar a mudança e indicar qual informação anterior deixou de valer.

## 10. S1-3 — Preparação do banco

### Por que

A aplicação precisava de uma estrutura para armazenar lojas, produtos, histórico de preços, eventos da coleta e usuários do painel.

### Como

Foi criado um usuário exclusivo com permissões limitadas e executado o script SQL. Depois, foram conferidos tabelas, índices, restrições, view e cadastros iniciais. Uma conexão autenticada via PHP/PDO validou o acesso.

### Para que

Permitir que o scraper grave os produtos e que o painel consulte as ofertas, mantendo os objetos da aplicação separados dos administrativos.

### Resultado

Estrutura criada e validada, com duas lojas cadastradas.

## 11. S1-4 — Coleta experimental

### Por que

Era necessário confirmar que os dados de um produto poderiam ser extraídos antes de implementar a gravação no banco.

### Como

Foi analisado o HTML público da KaBuM! e implementada a leitura dos dados estruturados para extrair nome, preço e disponibilidade. Foram adicionadas consulta ao `robots.txt`, espera entre requisições e validações dos campos.

### Para que

Estabelecer a primeira parte do fluxo de coleta, distinguindo produtos esgotados de páginas com dados ausentes ou inválidos.

### Resultado

Coleta real validada e 11 testes offline aprovados, sem gravação no banco.

## 12. S1-6 — Listagem de produtos em PHP

### Por que

Visualizar os produtos armazenados após a coleta.

### Como

Criada uma página PHP que consulta o Oracle via PDO, com configuração fora da pasta pública e formatação de preços em reais.

### Para que

Completar o fluxo inicial de coleta, armazenamento e exibição.

### Resultado

Produto exibido corretamente; página e CSS acessíveis; arquivos privados protegidos e falhas tratadas com mensagem genérica.

## 13. S2-1 — Coleta de vários produtos por categoria na KaBuM!

### Data e autorização

**17/11/2026.** O responsável validou o escopo antes das alterações: descoberta por categoria, paginação com limites, extração de imagem e preço original, coleta em lote, testes offline e atualização deste registro.

### O que foi feito e por que

A coleta anterior recebia apenas a URL de um produto. Foi criado `scraper/categorias.py` para descobrir e coletar vários produtos de GPU, SSD, RAM e CPU. O comando `scraper/coletar.py` passou a aceitar `--categorias`, mantendo o uso anterior por URL e `--categoria`.

O modelo `Produto` e o parser foram ampliados para imagem e preço original, quando disponíveis. A persistência agora grava esses campos sem apagar valores existentes quando a coleta não os informa. Isso prepara os dados usados na exibição de imagens e no cálculo de descontos.

### Como foi executado

Foram consultadas as páginas públicas da loja. A URL inicialmente examinada, `/hardware/ssd`, retornou uma estrutura sem catálogo e exibiu produtos recomendados após renderização. A conferência do breadcrumb de um produto identificou a categoria correta: `/hardware/ssd-2-5`. Nas quatro URLs corretas, o catálogo já estava disponível no HTML, dentro de `__NEXT_DATA__`, em `props.pageProps.data.catalogServer`.

As categorias utilizadas são:

| Categoria | Caminho |
| --- | --- |
| GPU | `/hardware/placa-de-video-vga` |
| SSD | `/hardware/ssd-2-5` |
| RAM | `/hardware/memoria-ram` |
| CPU | `/hardware/processadores` |

A descoberta lê apenas os códigos do catálogo correspondente à categoria e à página solicitadas. Links de recomendações e carrosséis não entram na coleta. A navegação usa `?page_number=2` e seguintes; o número retornado pela loja é conferido para detectar paginação incorreta. Os detalhes continuam sendo extraídos do `Product` em JSON-LD. O preço original vem de `product.prices.oldPrice` nos dados complementares, conferindo o identificador do produto; não é inferido a partir do preço parcelado.

O coletor consulta `robots.txt`, identifica o User-Agent, aguarda pelo menos dois segundos entre requisições, respeita um `Crawl-delay` maior e mantém cache em memória durante a execução. URLs são deduplicadas por categoria. Uma página sem catálogo válido gera falha, em vez de ser interpretada como categoria vazia ou produtos removidos.

Os limites padrão são uma página e 20 produtos tentados por categoria, incluindo produtos cuja coleta falha. O resumo informa contagens, páginas, falhas e interrupção por limite. Falhas de um produto não impedem os demais; cada gravação usa uma transação própria. O comando retorna código 1 quando há falhas. `--sem-gravar` permite conferir a coleta sem abrir conexão com o banco.

Playwright foi instalado temporariamente na `.venv` e utilizado com Edge em modo headless durante a inspeção. Após confirmar que o HTML das categorias corretas já contém o catálogo, a dependência foi removida, inclusive os resíduos da desinstalação. `requirements.txt` não foi alterado. A implementação final usa as bibliotecas já disponíveis no projeto.

### Como foi validado e qual foi o resultado

- **34 testes Python offline aprovados**, executados com `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Cobrem parser, persistência, categorias, paginação, duplicação, limites, bloqueio pelo `robots.txt`, cache, dados complementares inválidos e continuação após falhas de coleta ou gravação. O banco desses testes é SQLite em memória, sem acessar o Oracle local.
- As quatro páginas de categoria foram lidas com sucesso na inspeção. A segunda página de GPU também foi consultada, confirmando a mudança do número da página e dos produtos retornados.
- A execução real com `--categorias GPU SSD RAM CPU --max-paginas 1 --max-produtos 2 --sem-gravar` coletou dois produtos de GPU, dois de SSD e dois de RAM sem falhas. A categoria de CPU foi lida, mas as duas páginas de produto falharam por acesso à rede. O comando retornou código 1, com as falhas identificadas no resumo.
- Uma nova execução isolada de CPU, com os mesmos limites e sem gravação, coletou um produto. O produto `1053828` continuou apresentando falha de acesso; essa limitação permanece registrada, sem conclusão sobre estoque ou remoção.
- Foram adicionadas fixtures reduzidas de catálogo e de produto com imagem/preço original, baseadas no HTML público observado nesta data. São recortes para testes, não uma representação atualizada de preços nem uma cópia completa da listagem.

### Para que serve e como usar

Permite executar a coleta de uma ou mais categorias com volume controlado e persistir os produtos usando o fluxo existente:

```powershell
# Conferir sem acessar o Oracle
.\.venv\Scripts\python.exe -m scraper.coletar --categorias GPU SSD RAM CPU --max-paginas 1 --max-produtos 2 --sem-gravar

# Gravar no Oracle configurado no .env
.\.venv\Scripts\python.exe -m scraper.coletar --categorias SSD --max-paginas 2 --max-produtos 30
```

### Limitações e pendências

Nesta etapa não foi realizada gravação real no Oracle; a persistência dos campos novos foi validada em testes isolados. Uma execução limitada não cobre o catálogo inteiro e não permite inferir indisponibilidade pela ausência de um produto. Mudanças no formato dos dados da loja podem exigir ajuste no parser.

Histórico de preços, Terabyte, indisponibilidade por desaparecimento, links de afiliado e agendamento/logs continuam nas tarefas S2-2 a S2-6. Os testes permanecem em `unittest`, seguindo a base existente; a automação completa do CT-01 com pytest pertence à sprint 4.

O README foi atualizado com o estado da coleta e os comandos de uso e teste. As seções antigas que ainda apresentam diretórios como reservados e funcionalidades como planejadas refletem documentação inicial e precisam de uma revisão mais ampla em etapa futura. Nenhum commit ou push foi realizado nesta etapa; o versionamento exigido pela definição de pronto permanece pendente.

## 14. Recuperação da API de produtos — erro HTTP 503

### Data e autorização

**17/11/2026.** Após relatar erro em `/api/produtos.php`, o responsável autorizou iniciar o listener Oracle, validar a conexão e a rota e registrar o resultado. O diagnóstico inicial foi realizado sem alterar arquivos ou serviços.

### O que foi identificado e por que

O serviço `OracleServiceXE` estava em execução, mas `OracleOraDB21Home1TNSListener` estava parado. O comando `lsnrctl status` confirmou `TNS-12541: não há listener`. O PHP carregava o driver PDO `oci`, porém não conseguia estabelecer a conexão necessária para consultar os produtos. A API trata essa falha retornando HTTP 503 e uma mensagem genérica.

### Como foi corrigido

Foi executado `Start-Service -Name OracleOraDB21Home1TNSListener`. Logo após a partida, o listener ainda não conhecia o serviço da aplicação e a conexão retornou `ORA-12514`. Uma consulta administrativa somente de leitura confirmou `XEPDB1` em `READ WRITE`. Após o registro automático da instância, em aproximadamente um minuto, `lsnrctl status` passou a mostrar `xepdb1` como `READY`.

### Para que serve

O listener recebe as conexões do PHP e as encaminha ao serviço Oracle. A instância em execução, sozinha, não garante que a aplicação consiga conectar ao banco.

### Como foi validado e qual foi o resultado

Uma requisição HTTP real para `http://127.0.0.1:8080/api/produtos.php`, no servidor PHP já em execução, retornou **HTTP 200**, com JSON válido contendo **um produto**. Isso valida a conexão autenticada e a consulta da aplicação, além da recuperação da rota.

### Limitações e pendências

Não foi necessário alterar o código PHP, as credenciais, as tabelas ou os dados. O tipo de inicialização do serviço não foi modificado. Não foi determinada a causa da parada do listener; esta intervenção comprova a recuperação atual, sem comprovar funcionamento após reinicialização do Windows.

## 15. S2-2 — Módulo separado da Terabyte

**Registro histórico:** a implementação descrita nesta seção foi removida posteriormente por decisão do responsável. O estado atual da S2-2 está documentado na seção 16.

### Data e autorização

**17/11/2026.** O responsável validou previamente o escopo: módulo independente para GPU, SSD, RAM e CPU; campos do RF1; adaptação da persistência para a loja correta; opção `--loja terabyte`; testes offline; documentação; e tentativa de validação real limitada, sem gravação no Oracle. Também reforçou expressamente a atualização deste registro.

### O que foi feito e por que

Foi criado `scraper/terabyte.py`, sem importar o parser da KaBuM!. Os contratos `Produto`, `ColetaError` e `ResultadoCategoria` passaram para `scraper/modelos.py`, permitindo compartilhar os dados sem vincular a Terabyte ao HTML da outra loja. Os imports antigos de `Produto` e `ColetaError` por `scraper.kabum` e de `ResultadoCategoria` por `scraper.categorias` continuam funcionando.

O comando `scraper/coletar.py` passou a aceitar `--loja kabum|terabyte`, mantendo `kabum` como padrão e preservando os modos individual e em lote. A persistência aceita `loja_nome`, com padrão `Kabum`, e consulta a loja ativa correspondente antes de gravar. A identificação continua sendo a combinação de loja e código do produto: códigos iguais em lojas diferentes não se sobrescrevem.

### Como foi executado

A navegação pública da Terabyte, consultada pela ferramenta de pesquisa, confirmou os seguintes caminhos:

| Categoria | Caminho |
| --- | --- |
| GPU | `/hardware/placas-de-video` |
| SSD | `/hardware/hard-disk/ssd` |
| RAM | `/hardware/memorias` |
| CPU | `/hardware/processadores` |

Referências consultadas: [hardware](https://www.terabyteshop.com.br/hardware) e [robots.txt](https://www.terabyteshop.com.br/robots.txt). O acesso pela ferramenta de pesquisa não equivale a uma coleta bem-sucedida pelo cliente local.

As tentativas locais com Python e curl receberam HTTP 403 no `robots.txt`. A inspeção normal com Edge em modo headless também apresentou um desafio de acesso, sem fornecer o catálogo. Não foi implementada resolução de desafios, troca de identidade de bot ou qualquer mecanismo para contornar esse bloqueio. O Edge existente foi usado apenas para inspeção; não houve instalação de dependências novas.

Como não foi possível obter HTML real, foi preparado um parser de contrato com dados estruturados `Product`/`Offer` e `ItemList`, além de alternativa para links `a.prod-name`. **A existência desse seletor e dos dados estruturados na loja atual não foi confirmada.** As fixtures `terabyte_produto.html` e `terabyte_categoria.html` são sintéticas e têm essa origem declarada no próprio arquivo. Não devem ser apresentadas como páginas capturadas da loja.

O parser valida a identidade do produto, preço decimal em BRL e disponibilidade explícita. Produto disponível sem preço ou disponibilidade desconhecida gera falha. Imagem e preço original são opcionais; não são inventados quando ausentes. O preço original só é aceito quando marcado como `StrikethroughPrice`, conforme o [contrato Schema.org](https://schema.org/StrikethroughPrice); valores como `highPrice` ou preço parcelado não são tratados como preço anterior.

A leitura HTTP tem timeout, limite de resposta e verificação de domínio, inclusive antes de seguir redirecionamentos. O coletor aplica intervalo mínimo de dois segundos, considera `Crawl-delay`, mantém cache durante a execução, deduplica produtos e detecta páginas repetidas. Falhas de um produto não impedem o processamento dos demais.

A política de navegação reconhece `*` e `$`, grupos de User-Agent e regras específicas. Para consultas explicitamente proibidas, adota uma restrição adicional conservadora: um `Disallow` correspondente, como `/*?p=`, impede a navegação mesmo diante de um `Allow` mais amplo para a categoria. Não foram inventados endpoints alternativos para obter páginas proibidas. A paginação preparada só segue `rel="next"` da mesma categoria, após verificar a permissão e os limites.

Uma falha inicial de acesso ao `robots.txt` é reutilizada durante a execução para não repetir essa requisição a cada categoria. O comando informa as falhas e retorna código 1. A implementação não interpreta erro de acesso como produto indisponível e não remove dados.

### Para que serve e como usar

Permite selecionar o coletor da Terabyte mantendo a mesma interface de execução e persistência da KaBuM!:

```powershell
# Tentativa limitada, sem conexão com o Oracle
.\.venv\Scripts\python.exe -m scraper.coletar --loja terabyte --categorias GPU SSD RAM CPU --max-paginas 1 --max-produtos 1 --sem-gravar
```

O modo individual também aceita `--loja terabyte` e `--html`. Como no comando anterior da KaBuM!, o modo individual com HTML salvo **grava no banco configurado** e deve ser usado apenas com dados de teste. Os testes automatizados desse modo usam uma conexão simulada.

### Como foi validado e qual foi o resultado

- **58 testes Python offline aprovados**, incluindo os testes anteriores da KaBuM! e 24 testes novos de contrato Terabyte e persistência entre lojas. Foram executados com `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`.
- Os testes verificam campos do produto, ausência de preço, disponibilidade desconhecida, identidade, moeda, listagens, deduplicação, limites, paginação permitida e proibida, cache, bloqueio HTTP, redirecionamento externo, seleção do módulo e isolamento de dados entre lojas. A persistência foi validada em SQLite em memória.
- O comando real com `--loja terabyte --categorias GPU SSD RAM CPU --max-paginas 1 --max-produtos 1 --sem-gravar` retornou código 1 e informou HTTP 403 nas quatro categorias, originado no acesso inicial ao `robots.txt`. Nenhuma página de categoria foi coletada pelo comando e nenhum produto foi gravado. A requisição ao `robots.txt` não foi repetida por categoria.
- A ajuda do comando foi conferida e apresenta a opção `--loja`. Não houve gravação de teste no Oracle, alteração de esquema, alteração do PHP ou do agendamento.

### Limitações e pendências

**S2-2 permanece em validação, sem ser considerada concluída.** Há implementação e testes de contrato, mas eles não comprovam a compatibilidade com o HTML real da Terabyte. Para encerrar a tarefa, é necessário obter HTML real por acesso permitido, conferir ou ajustar os seletores e a fonte do preço original, substituir/complementar as fixtures sintéticas por recortes reais e concluir uma coleta real limitada com sucesso.

O bloqueio HTTP 403 e a restrição de paginação podem impedir a cobertura completa do catálogo; uma execução parcial não autoriza inferir desaparecimento de produtos. Histórico de preços (S2-3), indisponibilidade por desaparecimento (S2-4), afiliados (S2-5) e agendamento/logs (S2-6) não foram antecipados.

O README foi atualizado com o comando e com essa limitação. `requirements.txt` não mudou. Nenhum commit ou push foi realizado.

## 16. S2-2 em processo — integração Terabyte adiada e arquivos removidos

### Data e decisão

**17/11/2026.** O responsável decidiu deixar a Terabyte de lado nesta etapa e autorizou expressamente remover seus arquivos. Solicitou manter no README o status de integração em processo, com a explicação dos motivos.

### O que foi feito

Foram removidos `scraper/terabyte.py`, `tests/test_terabyte.py`, `tests/fixtures/terabyte_categoria.html` e `tests/fixtures/terabyte_produto.html`. Também foram retirados os dois testes de persistência específicos da Terabyte e os caminhos de seleção dessa loja no comando de coleta.

O comando voltou a operar somente com a KaBuM!, sem a opção `--loja`. A função de persistência voltou a selecionar a loja KaBuM!, preservando a coleta por categoria, os limites e os campos implementados na S2-1. `scraper/modelos.py` foi mantido porque contém contratos utilizados pelo código atual da KaBuM! e da persistência.

### Por que

A coleta local da Terabyte recebeu HTTP 403 já no `robots.txt`, e o Edge automatizado recebeu um desafio Cloudflare. Não houve acesso bem-sucedido ao HTML real para validar o coletor. Além disso, as [regras oficiais do programa de parceiros](https://www.terabyteshop.com.br/site/regras-programa-de-parceiros), consultadas nesta data, incluem proibição de coleta automatizada de informações. A aprovação como afiliado não constitui, por si só, autorização para executar o scraper.

Por decisão do responsável, o projeto seguirá com a KaBuM! enquanto a forma de acesso à Terabyte permanece em definição. A S2-2 está **em processo, adiada**, e não foi marcada como concluída. Para retomá-la, será necessário definir acesso autorizado com a empresa e validar a integração com dados reais. Não foi enviado contato à Terabyte nem confirmada a disponibilidade de API ou catálogo.

### Documentação

O README foi atualizado para refletir esse estado, explicar o bloqueio técnico e a restrição do programa de parceiros e retirar os comandos e referências aos arquivos removidos. A seção 15 deste registro foi preservada como histórico e recebeu uma indicação de que a implementação foi removida.

### Como foi validado e qual foi o resultado

Os **34 testes Python offline restantes passaram**, com `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`. A ajuda do comando foi conferida e não apresenta mais a opção `--loja`. A busca em `scraper` e `tests` não encontrou referências de código à Terabyte nem aos caminhos de seleção removidos.

### Limitações e pendências

Nenhuma coleta online ou gravação no Oracle foi executada nesta alteração. O script SQL original e os PDFs de planejamento foram preservados; o cadastro de loja previsto nesses documentos não significa que exista um coletor ativo. A remoção dos arquivos não executou exclusões de dados no banco. Nenhum commit ou push foi realizado.

## 17. S2-3 — Histórico do primeiro preço e das mudanças

### Data e autorização

**17/11/2026.** O responsável validou o escopo antes das alterações: registrar o primeiro preço conhecido, inclusive para produtos existentes sem histórico; registrar mudanças do preço atual sem duplicados; preservar histórico diante de preço ausente ou produto esgotado; manter produto e histórico na mesma transação; testar offline e atualizar a documentação, sem gravação no Oracle local.

### O que foi feito e por que

A função `salvar_produto`, em `scraper/banco.py`, foi ampliada para gravar em `HISTORICO_PRECO`, tabela já definida em `docs/01_criar_tabelas.sql`. Antes, a persistência atualizava o produto sem registrar seus preços anteriores. Agora o fluxo individual e o fluxo por categoria passam a manter a série de preços por meio da mesma função existente, sem novos comandos de coleta.

### Como foi executado

Foi mantido o bloqueio da linha da loja com `SELECT ... FOR UPDATE`, que serializa as gravações deste coletor no Oracle durante a transação. Após inserir ou atualizar o produto, a função consulta o último preço registrado para aquele produto. A ordenação usa `COLETADO_EM` decrescente e `ID` decrescente como desempate quando dois registros têm o mesmo instante.

Se a coleta informar preço e não existir histórico, é criado o primeiro ponto. Se já houver histórico, só é inserido outro ponto quando o preço coletado diferir do último preço registrado. A comparação usa os valores decimais do coletor e da coluna numérica, sem converter os preços para ponto flutuante. Preços numericamente iguais, como `100.0` e `100.00`, não geram duplicação.

Uma sequência `100 → 100 → 90 → 110 → 100` resulta em quatro registros: `100`, `90`, `110` e `100`. O retorno a um valor antigo é uma mudança válida; a deduplicação compara com a última observação, não com todos os preços já vistos.

Cada ponto inclui produto, preço, preço original conhecido e instante da coleta. O preço original ausente continua preservado no produto e esse valor conhecido é usado no novo ponto. Uma mudança apenas no preço original atualiza o produto, mas não cria nem modifica pontos de histórico, conforme o escopo validado.

Preço ausente não cria observação de histórico e não apaga registros existentes. Um produto cadastrado antes da S2-3 começa seu histórico na próxima coleta que informar preço; não são criados registros retroativos a partir do preço antigo armazenado ou da data de cadastro. Mudança de estoque isolada também não acrescenta pontos.

A gravação não tem commit próprio. Produto e histórico participam da transação aberta pelo chamador com `engine.begin()`. Se a inserção do histórico falhar, o chamador desfaz também a alteração do produto. O retorno da função continua contendo `id` e `acao`, preservando a interface dos comandos existentes.

### Para que serve

Permite manter o histórico exigido pelo RF2, evitando pontos repetidos a cada coleta e preparando os dados para o gráfico da sprint 3. Os comandos existentes passam a registrar histórico quando executados com persistência. O modo `--sem-gravar` continua sem abrir conexão com o banco e sem gravar produtos ou histórico.

### Como foi validado e qual foi o resultado

Foram aprovados **43 testes Python offline**, executados com:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os nove testes novos verificam primeiro preço, recoleta igual entre transações, queda, aumento, retorno a preço anterior, início do histórico de produto existente, mudança isolada do preço original, ausência de preço, preservação em esgotamento, separação entre produtos, desempate por ID e falha durante a inserção do histórico. Um mesmo teste cobre mais de um desses cenários. O teste anterior de rollback também foi ampliado para conferir que produto e histórico ficam vazios após falha posterior à gravação.

Para validar uma falha real do banco de teste durante a inserção, foi criado um trigger apenas no SQLite em memória que rejeita novos registros de histórico. Após tentar mudar o preço de `100` para `90`, a falha foi propagada, a transação desfeita e as consultas confirmaram que produto e histórico continuavam em `100`.

Os testes anteriores de parser, categorias, limites, tratamento de falhas e persistência também passaram. O README foi atualizado com o comportamento, o exemplo de preços, o status e os limites desta validação.

### Limitações e pendências

A implementação foi validada em SQLite em memória, sem acessar lojas ou gravar no Oracle local. O bloqueio concorrente do Oracle não foi exercitado por esses testes; foi preservado o mecanismo já utilizado pelo coletor. Não foram executadas migrações nem alterações de esquema, e nenhum dado real recebeu preenchimento retroativo.

A validação completa no Oracle e o CT-01 integrado continuam pendentes. A exibição do gráfico pertence à sprint 3. A Terabyte permanece adiada, e as tarefas S2-4 a S2-6 não foram antecipadas. Nenhum commit ou push foi realizado; o versionamento exigido pela definição de pronto permanece pendente.

## 18. S2-4 — Esgotamento, remoção confirmada e retorno ao estoque

### Data e autorização

**17/11/2026.** O responsável validou previamente o escopo: indisponibilidade por esgotamento ou remoção confirmada da página, preservação de preços e histórico, manutenção do estado diante de falhas de acesso, ausência em listagem limitada sem inferência de remoção, reativação por coleta válida e testes/documentação sem gravação no Oracle local.

### O que foi feito e por que

O parser já reconhecia `OutOfStock` e `Discontinued`. A S2-4 completou o fluxo para produtos cuja página desaparece, distinguindo remoção confirmada de falha transitória e permitindo revisar URLs cadastradas que deixaram de aparecer na listagem. A API passou a ocultar indisponíveis, mantendo seus registros e o histórico no banco.

### Como foi executado

Foi introduzida a exceção específica `PaginaRemovida`, com URL, código de produto e status HTTP. O acesso HTTP só produz essa confirmação quando recebe 404/410 na própria URL válida de produto, sem mudança de URL por redirecionamento. Erros em categoria ou `robots.txt`, bloqueios 403, falhas 503, timeout e respostas inválidas continuam como falhas de coleta.

A função `marcar_indisponivel` altera somente um produto existente da loja KaBuM! ativa. Mantém o bloqueio da linha da loja e a transação controlada pelo chamador. Define `DISPONIVEL = 0` e atualiza `ATUALIZADO_EM`, preservando nome, URLs, preços, `VISTO_EM` e histórico. Uma remoção de código não cadastrado retorna `nao_cadastrado`, sem inventar nome ou criar produto.

O comando individual trata essa confirmação e aplica a marcação. A coleta por categoria distingue produtos coletados, remoções confirmadas e falhas. Uma remoção não interrompe os demais produtos; uma falha na gravação da disponibilidade é informada e a transação é desfeita.

Para detectar produtos que saíram da listagem, a execução com persistência consulta URLs já cadastradas, exclui os códigos de produto já verificados na descoberta e revisa até `--max-produtos` URLs adicionais por categoria. A seleção prioriza `ATUALIZADO_EM` mais antigo, com desempate por ID, e inclui indisponíveis para detectar retorno. A conexão da consulta é encerrada antes do acesso à loja; não se mantém transação aberta durante requisições HTTP.

O limite da revisão é adicional ao da descoberta. Por exemplo, `--max-produtos 20` permite até 20 tentativas da listagem e até 20 revisões de cadastrados por categoria. O intervalo e o cache da sessão são compartilhados pelos dois fluxos. A ausência de um produto na listagem nunca altera seu estoque por si só; a própria URL precisa ser verificada.

O resumo ganhou `revisados`, `removidos` e `marcados_indisponiveis`. O último contador se refere às remoções HTTP aplicadas a cadastros existentes; esgotamento informado no HTML válido continua no fluxo normal de produtos coletados/gravados. O modo `--sem-gravar` não abre banco, não seleciona cadastrados para revisão e não aplica marcações.

Uma nova coleta válida com disponibilidade reativa o produto pelo fluxo de persistência existente. Um preço igual não acrescenta histórico. Também foi normalizado o preço zero de item esgotado para ausência de preço, evitando substituir o último valor conhecido por uma falsa queda para zero. Um preço positivo explicitamente informado continua sujeito à regra de histórico da S2-3.

A consulta de `web/api/produtos.php` passou a exigir `p.DISPONIVEL = 1`, além de loja ativa. O estado vazio da interface foi ajustado para “Nenhum produto disponível”, pois produtos cadastrados podem existir e estar esgotados. Não foi antecipada a home com ordenação por desconto da sprint 3.

### Para que serve

Evita exibir ofertas esgotadas ou removidas, preservando dados e permitindo reativação quando o estoque retorna. A revisão das URLs existentes fornece confirmação direta, em vez de inferir remoção a partir de uma varredura parcial do catálogo.

### Como foi validado e qual foi o resultado

- **55 testes Python offline aprovados**, com `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`.
- **3 testes da interface aprovados**, com `node tests/frontend.test.cjs`. A execução inicial com `node --test` foi impedida pela restrição de criação de subprocessos (`spawn EPERM`); a execução direta do mesmo arquivo concluiu os três casos.
- **Sintaxe PHP validada**, com `php -l web/api/produtos.php`, usando o executável PHP instalado na máquina.

Os 12 novos testes Python cobrem 404/410 de produto, 404 em categoria/robots ou após redirecionamento, falhas transitórias, esgotamento com zero, continuação após remoção, prévia sem gravação, preservação de preços e histórico, código desconhecido, rollback da marcação, seleção limitada de revisão e integração dos comandos com SQLite em memória. Os testes anteriores também passaram.

No teste integrado da coleta limitada, um produto cadastrado ficou fora da página de categoria simulada. A primeira revisão retornou falha 503 e o produto permaneceu disponível. A revisão seguinte confirmou 410 e marcou somente esse produto como indisponível. Isso valida a distinção entre ausência da listagem e remoção confirmada, sem acessar a loja ou o Oracle.

### Limitações e pendências

Não houve coleta online, gravação no Oracle local ou alteração de esquema nesta etapa. A rota PHP foi validada quanto à sintaxe; seu novo filtro ainda precisa ser exercitado no fluxo integrado com Oracle. Os testes de transação utilizam SQLite em memória e não exercitam concorrência Oracle.

A revisão é limitada por execução: nem todos os cadastrados serão verificados em um único lote quando houver mais produtos que o limite. Falhas preservam seus estados anteriores. O agendamento e os eventos em `LOG_COLETA` pertencem à S2-6; o comando ainda precisa ser executado para aplicar atualizações. A Terabyte permanece adiada. Nenhum commit ou push foi realizado, e o versionamento permanece pendente.

## 19. S2-5 — Conversor de link de afiliado KaBuM! com ID de teste

### Data e autorização

**17/11/2026.** O responsável validou o escopo para trabalhar somente com a KaBuM!: função isolada de conversão, ID de teste configurável enquanto não houver aprovação, gravação de `URL_AFILIADO` preservando `URL_ORIGINAL`, uso no botão “Ver na loja”, testes offline e documentação, sem gravação no Oracle local.

### Referências e decisão de formato

Foram consultados a [página oficial de afiliados da KaBuM!](https://www.kabum.com.br/hotsite/afiliados/), o [perfil KaBuM! na Awin](https://ui.awin.com/merchant-profile/17729) e a [documentação Awin com exemplos do formato de deeplink](https://help.awin.com/developers/docs/consent-framework-for-partners). A KaBuM! utiliza a Awin e seu anunciante é `17729`. O conversor usa o endpoint `https://www.awin1.com/cread.php`, com os parâmetros `awinmid`, `awinaffid` e `ued`.

O padrão de afiliado escolhido foi **`0`, placeholder local do projeto**. Não foi identificado nem utilizado um ID de sandbox oficial da Awin. Esse valor não foi apresentado como conta aprovada ou como garantia de rastreamento, redirecionamento ou comissão. Nenhum link Awin gerado foi aberto durante a implementação.

### O que foi feito e por que

Foi criado `scraper/afiliados.py`, com a função pura `gerar_link_afiliado`. Ela recebe URL original e ID, valida o escopo KaBuM!, monta os parâmetros com codificação de URL e retorna o deeplink sem acessar rede ou banco. A separação permite ajustar o formato posteriormente sem alterar o parser da loja.

A função `carregar_id_afiliado` usa `KABUM_AFILIADO_ID` do processo, depois do `.env` da raiz e, na ausência de ambos, o placeholder `0`. Valores vazios ou inválidos geram erro; o conversor aceita texto numérico não negativo de até 20 dígitos, sem zeros à esquerda em IDs diferentes de `0`. O arquivo `.env` real não foi alterado e não houve inclusão de credenciais no código.

O conversor aceita somente HTTPS em `www.kabum.com.br`, caminho de produto, sem parâmetros, fragmentos, credenciais, portas adicionais ou caracteres de controle. Links já convertidos não são aceitos como URL original. A URL original é mantida no parâmetro `ued`, codificada uma vez para transporte; uma decodificação do parâmetro recupera exatamente a entrada, inclusive quando ela já contém sequências percent-encoded. Os limites das colunas de URL original e afiliada são respeitados.

### Integração com persistência e interface

`salvar_produto` agora gera o link antes de modificar dados, usando a configuração atual. A gravação de `URL_AFILIADO` participa da mesma transação do produto e do histórico. O campo `URL_ORIGINAL` continua recebendo a URL original usada pelo scraper. Falhas de conversão tornam-se `PersistenciaError`, tratadas pelos comandos existentes. Não foi alterada a estrutura do banco.

Cada gravação válida renova o link, permitindo que uma futura troca do ID seja aplicada nas coletas seguintes. A troca apenas do ID, sem mudança de preço, não cria ponto de histórico. A marcação de indisponibilidade por remoção HTTP continua preservando os demais campos, incluindo o link existente. O teste anterior que esperava preservar um link arbitrário durante uma coleta foi ajustado: uma gravação válida agora deve manter um link gerado pelo conversor.

A consulta de `web/api/produtos.php` passou a incluir `URL_AFILIADO`, retornada no JSON como `url_afiliado`, sem retirar `url` (original). O JavaScript usa o link afiliado quando validado e usa a URL original segura quando o campo está vazio, ausente ou inválido, mantendo a navegação de cadastros anteriores.

O validador da interface exige HTTPS, domínio `www.awin1.com`, caminho `/cread.php`, anunciante `17729`, ID numérico, os três parâmetros esperados sem duplicação e destino correspondente à URL original do mesmo produto da KaBuM!. O link de afiliado recebe `rel="sponsored noopener noreferrer"`. A validação de URL original ficou restrita a produtos da KaBuM!, conforme o escopo atual sem Terabyte.

### Para que serve e como configurar

Implementa o RF4 no fluxo local: geração, persistência e exibição do link de saída, mantendo o ID em configuração e a URL original disponível para coleta.

```dotenv
KABUM_AFILIADO_ID=0
```

A ausência da variável também usa `0`. Configurar outro ID não atualiza imediatamente o banco: os produtos precisam ser gravados novamente pelos comandos de coleta. Não foram executadas atualizações de cadastros antigos nesta sessão. Para operação comercial, ainda serão necessários aprovação, ID real e validação dos links no programa Awin.

### Como foi validado e qual foi o resultado

- **63 testes Python offline aprovados**, com `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`.
- **5 testes da interface aprovados**, com `node tests/frontend.test.cjs`.
- **Sintaxe PHP aprovada**, com `php -l web/api/produtos.php`, usando o executável instalado na máquina.

Os seis testes novos do conversor cobrem formato, placeholder, ID configurável, preservação do destino, URLs/IDs inválidos, limites e prioridade de configuração. Os dois testes novos de persistência verificam geração/renovação do link sem alterar a URL original ou duplicar histórico e preservação dos dados diante de erro de conversão. A configuração de afiliado nos testes de banco é isolada do ambiente real.

Os dois testes novos da interface verificam o uso do link válido e a alternativa para links inválidos, incluindo outro domínio, outro produto, anunciante errado e parâmetros duplicados. Os testes anteriores de disponibilidade, histórico, coleta e interface continuaram passando.

A primeira tentativa do teste de configuração usou arquivo temporário, mas as permissões do ambiente impediram sua leitura/escrita. O teste passou a simular apenas a leitura do `.env`, exercitando a prioridade e a validação sem criar arquivos. A pasta temporária deixada pela tentativa foi removida após verificar seu caminho dentro do projeto.

### Limitações e pendências

Não houve coleta online, clique em links de afiliado ou gravação no Oracle local. A sintaxe da rota PHP foi verificada, mas o novo campo ainda precisa de validação integrada com Oracle. Os testes da interface usam DOM e API simulados e não comprovam navegação real pela Awin.

A S2-5 foi implementada e validada offline com placeholder; não houve aprovação de conta nem validação de atribuição de comissão. A Terabyte permanece adiada e seus arquivos não foram recriados. A S2-6, com agendamento e logs, continua pendente. Nenhum commit ou push foi realizado; o versionamento permanece pendente.

## 20. S2-6 — Eventos de coleta e preparação do agendamento

### Data e autorização

**17/11/2026.** O responsável validou implementar os arquivos de agendamento a cada 15 minutos, impedir execuções simultâneas, registrar resultados e mudanças em `LOG_COLETA`, preservar dados diante de falhas e não expor credenciais nos logs. Também foram autorizados testes offline e atualização da documentação. Foi combinado expressamente que a ativação do agendamento ficaria para validação separada, pois iniciará coletas e gravações reais.

### O que foi feito e por que

Foram implementados eventos na persistência e resultados nos comandos de coleta. Foi criado `scraper/execucao.py` para trava entre processos e log local de apoio, `scraper/agendado.py` como entrada do Agendador e `scripts/preparar_agendamento.ps1` para produzir um XML desabilitado, sem registrar ou iniciar tarefa.

Antes desta etapa, não havia execução programada nem eventos persistidos sobre o resultado da coleta. A implementação prepara a operação recorrente e os dados que serão usados pelo painel de monitoramento da sprint 3.

### Eventos e transações

`salvar_produto` passou a comparar os dados anteriores do produto e registrar `PRODUTO_NOVO`, `PRECO_ALTERADO`, `ESGOTADO` e `VOLTOU_ESTOQUE` quando houver essas mudanças. As recoletas iguais não duplicam eventos de transição. O primeiro preço conhecido não é tratado como alteração de preço anterior inexistente. Produto, histórico e seus eventos participam da mesma transação; uma falha de inserção de evento desfaz também a mudança de preço e o histórico.

`marcar_indisponivel` registra `ESGOTADO` somente quando o produto passa de disponível para indisponível. Uma nova confirmação 404/410 de produto que já estava indisponível não repete essa transição.

O comando registra `COLETA_OK` após uma operação individual ou categoria sem falhas e `COLETA_FALHA` diante de falhas de coleta, revisão ou persistência. Cada falha de categoria é registrada e, quando a URL corresponde a produto cadastrado, o evento é associado ao produto. Esses registros usam transações separadas da operação desfeita, para que o diagnóstico sobreviva ao rollback. A seleção da loja é restrita à KaBuM!.

As mensagens persistidas são geradas de um conjunto fixo e podem incluir apenas a categoria validada. Não recebem mensagens brutas de exceção, parâmetros SQL, URLs, nomes de produtos ou credenciais. O esquema existente de `LOG_COLETA` foi utilizado sem alterações de tabelas.

### Trava e falha de infraestrutura

A entrada comum do coletor agora adquire uma trava não bloqueante em `.coleta.lock`, usando `msvcrt` no Windows e `flock` em sistemas compatíveis. A proteção se aplica a coleta individual, lote e entrada agendada no mesmo diretório de projeto. Se outra execução já tiver a trava, o comando informa que foi ignorado e retorna código 2 antes de abrir o banco ou consultar lojas.

A trava é liberada na saída normal ou por exceção e pelo sistema operacional ao encerrar o processo. O arquivo não é removido durante o uso, evitando disputa entre processos sobre arquivos diferentes com o mesmo nome. Sua existência não significa que esteja travado. O `.gitignore` foi ampliado para ignorá-lo.

Se não for possível registrar resultados no banco, o comando retorna falha e tenta gravar uma mensagem local fixa em `logs/coleta.log`. Configuração indisponível também tem apoio local. `scraper.agendado` registra um resultado geral de sucesso, falha ou execução ignorada; falhas inesperadas não têm traceback ou conteúdo de exceção serializado nesse log.

O arquivo local tem rotação de 1 MiB e três cópias, horário explícito UTC−04:00 de Manaus e diretório já ignorado pelo Git. Se o armazenamento local também falhar, o log não pode ser garantido; isso não muda o código de falha original. A coleta com `--sem-gravar` continua sem acesso ao banco e sem eventos em `LOG_COLETA`, mas também respeita a trava local.

### Preparação do Windows

Foram consultadas as referências oficiais Microsoft de [repetição](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-repetition-triggerbasetype-element), [política de instâncias](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-multipleinstancespolicy-settingstype-element) e [estado habilitado](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskschedulerschema-enabled-settingstype-element).

O script de preparação gera `logs/coleta-kabum.xml` com caminhos absolutos da `.venv` e do projeto, usuário atual sem senha, execução pelo `pythonw.exe` e módulo `scraper.agendado`. O início é definido para 15 minutos após a preparação, com offset de Manaus. O intervalo é `PT15M`, sem duração final; a política é `IgnoreNew` e a tarefa tem `Enabled=false`.

A configuração usa a sessão interativa do usuário, privilégios mínimos, alimentação externa e não acorda o computador. O tempo máximo da execução foi desabilitado para não interromper uma coleta longa; se ela ultrapassar o intervalo, os disparos sobrepostos são ignorados. `StartWhenAvailable` permite uma ocorrência vencida quando a tarefa estiver disponível, o que deve ser considerado ao ativá-la posteriormente.

O script apenas escreve o XML dentro do projeto. Não contém chamada de registro, habilitação ou início de tarefa. O arquivo gerado é local e ignorado pelo Git. Não houve instalação de dependências ou alteração de credenciais, serviços Oracle ou configurações do Windows nesta etapa.

### Como usar

Preparação sem executar coleta ou registrar tarefa:

```powershell
.\scripts\preparar_agendamento.ps1
```

A futura entrada agendada executará uma página de GPU, SSD, RAM e CPU, com até 20 produtos da descoberta e até 20 revisões de cadastrados por categoria. A execução do módulo `scraper.agendado` efetivamente coleta e grava no banco; não foi executada com dados reais nesta sessão. A importação, a ativação e a primeira execução real ficam pendentes de autorização separada.

### Como foi validado e qual foi o resultado

**75 testes Python offline aprovados**, com:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Os 12 testes novos verificam transições sem duplicação, remoção repetida, falha do log com rollback de produto/histórico, mensagens fixas, persistência de falha após rollback, trava concorrente, liberação por exceção, bloqueio de outro processo, execução ignorada sem abrir banco, argumentos da entrada agendada, captura sanitizada de falha inesperada e apoio local quando o banco rejeita o log. Um teste foi usado para mais de um desses cenários. Os testes existentes também passaram; testes que simulavam a persistência foram ajustados para considerar a transação adicional do resultado.

O script PowerShell foi executado somente para preparar o arquivo. O XML resultante foi lido, confirmando `PT15M`, `Enabled=false`, `IgnoreNew` e `-m scraper.agendado`. A definição XML foi atribuída a uma tarefa em memória pela interface COM `Schedule.Service.NewTask`, que a aceitou; nenhuma chamada de registro foi feita. Essa verificação valida a definição no Agendador disponível na máquina sem criar uma tarefa persistente.

### Limitações e pendências

Nenhuma tarefa foi registrada ou ativada. Não houve coleta online, clique em link afiliado ou gravação no Oracle local. Os eventos foram validados em SQLite em memória. A integração com Oracle, a execução real pelo Agendador, a disponibilidade do usuário/computador e os resultados entre disparos ainda precisam ser validados após autorização.

A S2-6 tem implementação e preparação validadas offline, mas a ativação e a operação recorrente continuam pendentes. A Terabyte permanece adiada. O painel de monitoramento pertence à sprint 3 e os três dias de estabilidade à sprint 4. Nenhum commit ou push foi realizado; o versionamento permanece pendente.

## 21. S3-1 — Home de promoções

A home consulta `V_PROMOCOES_ATIVAS`, mantém apenas ofertas de lojas ativas e aplica o filtro de categoria antes de limitar a lista a 100 resultados. A ordenação usa o maior desconto e desempata pela atualização mais recente e pelo ID. Os cards mostram o preço atual, o preço original e o desconto, com o link de loja já validado pela interface.

Passaram os 6 testes da interface (`node tests/frontend.test.cjs`), os 75 testes Python offline e a verificação de sintaxe do PHP. A API retornou HTTP 400 para categoria inválida. O listener do Oracle XE local continuou parado após uma tentativa de iniciar o serviço, e o endereço configurado não respondeu às tentativas de conexão. A consulta e a ordenação com ofertas reais ainda precisam ser confirmadas. A próxima entrega do backlog é a S3-2, página do produto com gráfico de histórico.

## 22. Recuperação da API de promoções

### Data e sintoma

Em 18/11/2026, foi relatado erro HTTP 503 ao consultar as promoções. Durante o diagnóstico, a rota sem extensão também retornou HTTP 404 no roteador local.

### Causa e correção

O log do Oracle confirmou o erro `TNS-12545`. O listener tentava escutar em um IP que a máquina já não possuía. Foi criado um backup de `listener.ora` e `tnsnames.ora` antes de configurar `127.0.0.1` nos dois arquivos e em `DB_HOST` no `.env` local. Com o listener iniciado, o endereço de `LOCAL_LISTENER` foi atualizado em memória e `ALTER SYSTEM REGISTER` registrou `xepdb1` no listener.

O roteador PHP passou a aceitar `/api/produtos` como alias de `/api/produtos.php`, preservando o parâmetro `categoria`. O servidor PHP da porta 8080 foi reiniciado após a recuperação da conexão.

### Validação e pendências

Na porta 8080, `/api/produtos`, `/api/produtos.php?categoria=GPU` e `/api/produtos?categoria=GPU` retornaram HTTP 200 com `{"produtos":[]}`. Em um servidor de teste, uma categoria inválida retornou HTTP 400. A lista vazia confirmou a execução da consulta. A ordenação com ofertas reais e o registro automático do listener após reinicialização do Oracle ainda precisam ser verificados.

## 23. S3-2 — Página do produto e histórico de preços

### O que foi feito

O nome do produto no card abre `/produto.html?id=<id>`. A página reutiliza a exibição do preço, da disponibilidade e do botão **Ver na loja**, incluindo a validação do link afiliado. A API consulta `HISTORICO_PRECO` pelo ID interno do produto e retorna os registros em ordem cronológica. A página exibe os valores em um gráfico Chart.js 4.5.1 servido localmente e em uma tabela com data, hora e preço.

### Validação e aceite

Passaram 9 testes de interface, incluindo navegação pelo card, envio de dois preços simulados ao gráfico, conteúdo da tabela e estado sem histórico. Também passaram 75 testes Python offline e a verificação de sintaxe do PHP. Com o Oracle local, a página, a API do produto 1 e o arquivo do Chart.js responderam HTTP 200. A API devolveu HTTP 400 para ID inválido e HTTP 404 para produto inexistente.

O produto 1 estava sem registros em `HISTORICO_PRECO`. O aceite visual foi solicitado ao responsável. A primeira verificação é abrir `http://127.0.0.1:8080/produto.html?id=1` e conferir os dados, o botão **Ver na loja** e a mensagem de histórico vazio. Com um produto que tenha preços registrados, falta conferir no navegador os pontos do gráfico, seus valores e a correspondência com a tabela.

### Dados de teste para validar o fluxo pela home

O SSD Kingston NV3 (ID 1) estava disponível, mas ficava fora da home porque o preço original era nulo. No Oracle local, o produto recebeu preço original fictício de R$ 1.349,99 e dois registros de teste de R$ 1.249,99 e R$ 1.149,99. A API retornou o produto na listagem geral e no filtro SSD, com 15% de desconto. O endpoint de detalhes devolveu os dois preços em ordem cronológica. A validação visual agora pode começar na home e seguir pelo nome do SSD até o gráfico, a tabela e o botão **Ver na loja**.

## 24. S3-3 — Login do painel administrativo

### Implementação

O cadastro pelo PowerShell pede a senha e a confirmação em prompts ocultos e envia a senha ao PHP pela entrada padrão. O Oracle armazena somente o hash Argon2id em `USUARIO.SENHA_HASH`. O login usa consulta parametrizada e `password_verify()`, com a mesma mensagem de erro para e-mail desconhecido e senha incorreta.

O roteador exige uma sessão autenticada em `/painel`. O login renova o ID da sessão, o logout invalida a sessão e a inatividade expira após 30 minutos. Os formulários de login e logout exigem token CSRF. O cookie usa `HttpOnly` e `SameSite=Strict`, com `Secure` em HTTPS. O controle de login limita a origem a 10 tentativas em cinco minutos, independentemente da sessão. A home e as páginas de produto continuam públicas.

### Validação

Uma conta descartável no Oracle confirmou o hash Argon2id, o redirecionamento sem sessão, o login válido e inválido, a renovação do cookie, a proteção CSRF e o logout. A conta foi removida ao fim do teste. Um teste isolado do controle de tentativas confirmou o bloqueio na 11ª tentativa. Passaram também os 9 testes de interface, os 75 testes Python e a verificação de sintaxe do PHP.

O cadastro do administrador definitivo depende de uma senha escolhida pelo responsável no terminal. A S3-4 vai usar a sessão administrativa para proteger os dados de monitoramento da coleta.

## 25. S3-4 — Monitoramento da coleta

O painel autenticado mostra o resultado e o horário da última tentativa registrada por loja. Eventos de preço ou estoque aparecem na atividade recente e o status da loja usa apenas `COLETA_OK` e `COLETA_FALHA`. A lista mostra até 20 eventos por ordem decrescente de data, com desempate pelo ID e o nome do produto quando houver. As consultas ao Oracle são somente de leitura.

Foram verificados o redirecionamento de `/painel` para `/login` sem sessão, a resposta HTTP 503 com mensagem genérica e logout disponível em uma falha de banco simulada, e a renderização dos estados e eventos com dados simulados. Passaram a verificação de sintaxe do PHP, os 9 testes da interface pública e os 75 testes Python.

O teste automatizado do painel autenticado com o Oracle local ficou pendente porque a revisão automática de permissão expirou. Para o aceite visual, entrar em `/painel`, conferir o cartão da KaBuM! e verificar a tabela quando houver eventos de coleta registrados. Ao sair, abrir `/painel` novamente e confirmar o retorno à tela de login.

A Terabyte foi retirada dos cartões e da lista de eventos do painel após a decisão de não usar dados dessa loja. O filtro é aplicado nas consultas, e o cadastro e os registros existentes no Oracle foram preservados.

## 26. S4-1 — Revisão das fixtures HTML da KaBuM!

Foram revisados os três arquivos já salvos em `tests/fixtures`:

| Fixture | Cobertura |
| --- | --- |
| `kabum_categoria.html` | Recorte da primeira página de GPUs. Preserva a estrutura do catálogo, três códigos de produto e o total de páginas. |
| `kabum_produto.html` | Recorte do SSD Kingston NV3 com SKU, nome, preço e disponibilidade. Permite verificar a ausência de preço original e imagem. |
| `kabum_produto_completo.html` | Recorte do mesmo SSD com preço original e imagem. Serve de base para testar desconto e persistência. |

Os 75 testes offline passaram com `python -m unittest discover -s tests -q` no ambiente virtual. As listagens de SSD, RAM e CPU são simuladas nos testes. Mudanças de preço, esgotamento e falhas HTTP também são simulados. Os recortes existentes servem de base para começar a automatizar o CT-01 na S4-2. A cobertura de HTML observado por categoria ainda se limita a GPU.

A revisão foi feita com os arquivos locais, sem novas capturas ou conexão com o Oracle. A Terabyte ficou fora do escopo.

## 27. S4-2 — Automação do CT-01 com pytest

O teste `tests/test_ct01.py` usa a fixture HTML da KaBuM! e adapta o esquema do Oracle para um arquivo SQLite temporário compartilhado pelo coletor e pelo PHP. O caso exercita as rotas PHP por CGI, executa o JavaScript da Home e do produto em um DOM simulado no Node.js e autentica uma conta descartável no banco de teste. As alterações de preço e estoque são geradas em cópias temporárias da fixture.

O cenário verifica cadastro de produto e imagem, a primeira observação de preço, a ausência de duplicação e a queda de R$ 2.399 para R$ 1.899. Confere o desconto de 21%, a ordem da Home em relação a outra oferta, os dois pontos do gráfico, o link Awin com ID de teste e a saída da Home quando o produto se esgota. Também simula um HTTP 503 da KaBuM!, verifica que oferta e histórico são preservados e confere a falha e a recuperação no painel protegido por login.

A falha prevista para a Terabyte no PRD foi simulada na KaBuM!, a única loja em uso. O teste não faz requisições às lojas, não acessa o Oracle local e não mede tempo de renderização em navegador. A medição no celular permanece na S4-4 e a operação de três dias na S4-5.

Validação com `python -m pytest -q` no ambiente virtual: 76 testes e 65 subtestes aprovados.

## 28. S4-3 — Preservação dos dados e aviso de falha

Os lotes com mais de uma categoria passaram a registrar um resultado consolidado em `LOG_COLETA`. Assim, uma categoria bem-sucedida no fim da execução não mascara uma falha em uma categoria anterior. Os eventos individuais continuam disponíveis no painel. Falhas de rede, de interpretação ou de persistência preservam os dados das operações que não foram confirmadas.

O painel autenticado destaca a falha mais recente da loja e informa que os dados das operações que falharam foram preservados. Se uma falha de infraestrutura impedir o registro no banco, o painel pode exibir a data do último aviso a partir de `logs/coleta.log`. Essa leitura é limitada ao fim do arquivo e mostra uma mensagem fixa. Uma execução agendada bem-sucedida encerra o aviso local.

Os cenários automatizados cobrem um lote com falha seguida de sucesso em outra categoria, a preservação da oferta e do histórico, o desaparecimento do aviso após um lote bem-sucedido e a exibição do aviso local quando o evento não chega ao banco. Os testes usam banco temporário e não executam uma coleta real.

Validação: 78 testes e 65 subtestes no pytest, 10 testes de interface e verificação de sintaxe dos arquivos PHP alterados.

## 29. S4-4 — Tempo de carregamento da Home no celular

Foram feitas cinco navegações com cache HTTP do navegador desabilitado no Edge 157, em viewport de 390 × 844 px, CPU limitada a 4×, latência de 150 ms e rede de 1,6 Mb/s de download e 0,75 Mb/s de upload. O servidor PHP e o Oracle estavam no computador local. A Home usou a única oferta de teste disponível no banco.

| Rodada | Primeira oferta renderizada | LCP |
| --- | ---: | ---: |
| 1 | 1.282 ms | 1.288 ms |
| 2 | 699 ms | 704 ms |
| 3 | 719 ms | 724 ms |
| 4 | 711 ms | 716 ms |
| 5 | 696 ms | 700 ms |

O tempo da primeira oferta foi medido da navegação até o primeiro ciclo de pintura após o destaque e o card estarem presentes no DOM. A mediana foi de **711 ms**. Todas as rodadas ficaram abaixo da meta de **2 s**, por isso o código da Home não precisou de ajustes. O resultado corresponde à simulação local com uma oferta. A medição em aparelho físico ou com catálogo maior não faz parte deste resultado.

A S4-5 aguarda autorização para a primeira coleta real limitada da KaBuM! e para a janela de três dias de operação. Nenhuma coleta nova foi executada nesta etapa.

## 30. S4-5 — Janela de três dias de operação local

Em 18/11/2026, após autorização, foi executada uma coleta real limitada da KaBuM! com uma página de GPUs e até um produto. O coletor gravou uma placa ASRock RX 7600 (ID 21) no Oracle, com um ponto de histórico. A API da Home confirmou o preço de R$ 1.999,99, o preço original de R$ 2.941,16 e o desconto de 32%. A oferta de SSD do teste anterior contém valores simulados e não serve como evidência dessa coleta.

A tarefa `ProjPromo-S4-5-KaBuM` foi registrada com repetição de 15 minutos e janela de **18/11/2026 às 11:26 a 21/11/2026 às 11:26**, no horário de Manaus. A tarefa usa a sessão do usuário conectado e alimentação externa. Os disparos perdidos não são executados posteriormente. A validação usa os resultados de execução em `logs/coleta.log` e os eventos em `LOG_COLETA`. A S4-6 aguarda aprovação separada após a janela.

O Agendador confirmou o primeiro disparo às 11:26. A tarefa `ProjPromo-S4-5-Resumo` foi programada para 21/11/2026 às 11:31, com geração de `logs/s45-resultado.json`. O resumo conta sucessos e falhas observados em cada período de 24 horas e informa os 96 disparos previstos por período. A diferença entre o previsto e os resultados registrados ajuda a identificar lacunas na janela.

O primeiro lote terminou às 11:31 com `EXECUCAO_FALHA`. O Oracle registrou 43 novos produtos e falhas em GPU (1 evento), SSD (5), RAM (5) e CPU (6), além do resultado consolidado de falha. A API respondeu com 28 ofertas ativas, incluindo a oferta de teste anterior. Os eventos no Oracle registram a categoria e o resultado, mas não detalham a causa específica de cada falha. Esse lote conta como execução com falha na janela. A estabilidade só será avaliada após a coleta dos resultados dos três dias.

### Investigação do primeiro lote

Os 17 eventos de falha por categoria não estavam associados a produtos já cadastrados. Uma reprodução somente de leitura comparou a primeira página das categorias SSD e CPU com o cadastro do Oracle e tentou abrir dois produtos ausentes de cada categoria, respeitando o intervalo e o `robots.txt`. Três páginas foram lidas normalmente. O produto CPU 181089 retornou uma falha de acesso durante a amostra e foi lido normalmente em uma tentativa isolada posterior.

A reprodução confirmou uma falha intermitente de acesso a uma página da KaBuM!. O primeiro lote gravou produtos nas demais operações, e seus logs não contêm detalhe suficiente para atribuir uma causa aos 17 eventos. A investigação não gravou produtos nem alterou o coletor ou o agendamento.

### Diagnóstico das execuções seguintes

Foi adicionada a entrada `DIAGNOSTICO_COLETA` ao log local dos lotes agendados com falha. Ela registra contagens por categoria e códigos fixos de causa, distinguindo falhas de rede, HTTP, interpretação dos dados e transações no banco. URLs, exceções brutas e credenciais ficam fora desse registro. A cadência e os limites de coleta foram mantidos. Passaram 79 testes e 65 subtestes no pytest.

O segundo lote terminou às 11h45 com nove erros de decodificação: um em GPU, três em SSD e cinco em RAM. O log desse lote não identificou falhas de gravação. Em duas páginas reproduzidas, a KaBuM! respondeu com `Content-Encoding: gzip` e assinatura binária `1f8b`. O coletor tentava interpretar esses bytes como UTF-8 antes de descompactá-los.

O coletor passou a descompactar gzip antes de decodificar e a limitar o tamanho da resposta antes e depois da descompactação. Dois testes offline cobrem conteúdo válido, conteúdo truncado e expansão acima do limite. As duas páginas foram lidas novamente sem gravação no Oracle. A correção entrou durante a janela S4-5, após o segundo lote. As causas individuais das 17 falhas do primeiro lote continuam indeterminadas.

Uma nova leitura do produto 459144 confirmou a extração com `Content-Encoding: gzip`, sem persistência. A suíte passou com 81 testes e 67 subtestes.

O primeiro lote agendado após a correção terminou em 18/11/2026 às 12h01, no horário de Manaus, com `EXECUCAO_OK`. A janela da S4-5 continua em andamento e os dois lotes anteriores permanecem registrados como falhas.

O lote seguinte, iniciado às 12h11 e concluído às 12h16, atualizou o horário de última consulta de 80 produtos no Oracle. Não houve cadastro novo, mudança de preço ou mudança de disponibilidade registrada nesse lote. A API retornou 47 ofertas ativas e a Home renderizou os 47 cards no Edge.

### Resultado da janela e recuperação

Entre 18/11 às 11h26 e 21/11 às 11h26 (Manaus), o log registrou **39 sucessos e 3 falhas**, de 288 disparos previstos. A diferença é de 246 horários previstos sem resultado contabilizado. O resumo original tinha omitido o sucesso de 19/11 às 08h16 porque a linha começava com uma vírgula avulsa. O log também mostrou sete avisos de contenção da trava quase simultâneos em 19/11, com possibilidade de mensagens duplicadas na versão anterior.

Após a correção do gzip em 18/11, não voltou a aparecer o código `CODIFICACAO`. Em 19/11 às 07h11, o lote registrou 84 falhas de DNS em quatro categorias. Em 22/11 às 17h31, fora da janela oficial, houve mais 20 falhas de DNS em três categorias, seguidas de nove execuções bem-sucedidas até 19h54. Na janela oficial, o maior intervalo entre resultados foi de cerca de 43 horas, entre 19/11 às 14h10 e 21/11 às 09h15. O log disponível não permite atribuir cada lacuna a uma causa. A tarefa temporária dependia de sessão aberta e alimentação externa, sem recuperação de disparo perdido.

O coletor passou a repetir a requisição uma vez após uma falha de DNS e a suspender pedidos à loja por 30 segundos se a repetição falhar. O log local agora usa uma trava exclusiva durante a gravação e rotação, registra o início de cada entrada agendada e emite um único aviso quando a coleta é ignorada por concorrência. O resumo recupera a linha legada sem reescrever o log.

O XML de recuperação conserva a cadência de 15 minutos e a retomada quando disponível, limita cada execução a 30 minutos e permite habilitar a execução na bateria e solicitar ativação da suspensão. Foi gerado com essas duas opções para revisão. O XML ainda depende da sessão do usuário e do Oracle local. A consulta ao Agendador falhou neste ambiente, e o XML não foi aplicado à tarefa ativa.

O histórico operacional do Agendador estava desabilitado na consulta. A validação offline passou com 85 testes e 73 subtestes. Uma verificação de escrita concorrente gravou 80 linhas JSON válidas com oito processos.

### Segunda janela da S4-5

A tarefa permanente `ProjPromo-KaBuM` foi atualizada com a configuração de recuperação. A nova janela vai de **23/11/2026 às 18h28m51s a 26/11/2026 às 18h28m51s**, no horário de Manaus. A tarefa anterior de coleta da S4-5 já não tinha próximos disparos. A tarefa de resumo foi reagendada para **26/11 às 19h03m51s**, com retomada quando disponível. Ela grava `logs/s45-revalidacao.json` e preserva o resumo da primeira janela.

O início e o resultado de cada processo agendado passaram a compartilhar um identificador. O relatório conta tentativas que começaram dentro da janela, inclusive quando uma delas termina depois da hora de encerramento. Como o PRD deixa a taxa mínima em aberto, a referência provisória adotada para a KaBuM! é de pelo menos **92 sucessos entre 96 disparos previstos por período de 24 horas**. A execução depende da sessão do Windows, do Oracle e da rede. O Windows negou acesso à ativação do histórico operacional do Agendador.

O primeiro disparo foi confirmado em `logs/coleta.log` às 18h29m00s. A suíte passou com 86 testes e 73 subtestes, incluindo a atribuição de um resultado à janela pelo horário de início.

## 31. S4-6 — Revisão e retrospectiva

Na primeira janela, o CT-01 confirmou o fluxo de promoção no ambiente de teste, a trava protegeu contra execuções concorrentes e a coleta real gravou ofertas exibidas pela Home. As lacunas do agendamento e os erros de DNS limitaram a cobertura observada. A segunda janela registra horários de início e desfecho e usa uma configuração que retoma execuções quando o computador volta a estar disponível.

Uma consulta somente de leitura ao Oracle sobre a primeira janela encontrou 218 eventos de produto novo e 94 eventos de preço alterado. A comparação de cada ponto do histórico com o ponto anterior do mesmo produto encontrou zero registros consecutivos com o mesmo preço.

Em 23/11/2026, a revisão preliminar manteve o MVP 1 em validação enquanto o escopo de lojas e o momento da verificação de estabilidade estavam em aberto.

Em 24/11, entre 08h34m30s e 08h34m31s, a primeira execução da suíte de testes gerou sete avisos `EXECUCAO_IGNORADA` enquanto o lote agendado estava ativo. Esses avisos vieram dos testes e ficam fora da contagem de resultados da janela. A suíte passou a usar pasta, trava e log temporários.

**Decisão final em 24/11/2026: encerrar a revisão S4-6 e prosseguir com o desenvolvimento do MVP 2.** A KaBuM! é a única loja exigida para a validação. A conferência das 72 horas consecutivas foi transferida para o encerramento do projeto. A S4-5 permanece com a validação de estabilidade pendente e o agendamento atual continua disponível para coletar evidências.

Na revisão, passaram 86 testes e 73 subtestes, incluindo o CT-01 com a KaBuM!, a preservação do histórico e o aviso de falha no painel. Na retrospectiva, ficam como práticas a manter os testes isolados, o registro do início e do resultado dos lotes e a preservação dos dados em falhas de rede. A suspensão do computador e a duração de um lote completo acima de 15 minutos são fatores a considerar na validação final. O versionamento continua pendente porque a branch `main` ainda está sem commits.

## 32. MVP 2 — Preparação do PostgreSQL

O coletor Python e o PHP passaram a aceitar `DB_DRIVER=postgresql` em um ambiente separado, com esquema próprio e conexão TLS. A configuração padrão continua usando o Oracle durante a S4-5. A carga de dados, o CT-01 em um PostgreSQL real e a publicação na Render permanecem pendentes.

## 33. S5-1 — Banco de produção e local da coleta

Em 24/11/2026, foi escolhido o **PostgreSQL** como destino da migração do Oracle. O projeto já tem o esquema, a visão `V_PROMOCOES_ATIVAS`, o índice do histórico por produto e data e as conexões PHP e Python preparadas. A Render oferece PostgreSQL gerenciado, o que reduz o trabalho de operação do banco se a publicação seguir nessa plataforma.

A escolha inicial para o **coletor Python** é executá-lo em Linux no ambiente de produção, com agendamento no servidor, para que a coleta funcione com o computador local desligado. Antes de ativar o agendamento, será validado o acesso à KaBuM! a partir desse ambiente. Se o teste indicar bloqueio, será reavaliada a alternativa do PRD de executar o coletor localmente e enviar os dados por uma API autenticada.

A S5-2 prevê a criação do banco no servidor. Na S5-3, a carga deve preservar os IDs e o histórico de preços, e o CT-01 deve ser repetido no PostgreSQL. O Oracle será mantido como cópia até a virada estar estável. A publicação e o agendamento do coletor ficam na S5-5.

## 34. S5-2 — Esquema PostgreSQL e preparação do servidor

Em 24/11/2026, o esquema PostgreSQL existente foi comparado com o do Oracle. Ele já contempla as cinco tabelas, as colunas de identidade, os preços com duas casas decimais, os indicadores 0/1, os índices de histórico e coleta, a visão `V_PROMOCOES_ATIVAS` e os cadastros iniciais das lojas. A revisão confirmou que o script cobre a estrutura prevista para esta etapa.

O README passou a documentar a aplicação transacional do esquema por `psql`, com TLS e interrupção em caso de erro, além das consultas para conferir tabelas, índices, lojas e visão de ofertas.

**Status: concluída no ambiente local.** O escopo desta etapa foi ajustado para o Windows local. O banco `proj_promo` foi criado no PostgreSQL 19.0, em `127.0.0.1:5432`, e recebeu o esquema inicial. A conferência pelo `psql` retornou cinco tabelas, dez índices (incluindo os de histórico e coleta), os cadastros de Kabum e Terabyte e zero ofertas na visão `V_PROMOCOES_ATIVAS`. A opção `-P pager=off` permitiu exibir os resultados após o paginador tentar chamar `cat` no Windows.

A importação dos dados do Oracle e o CT-01 no PostgreSQL ficam na S5-3. O provisionamento em hospedagem externa fica para uma etapa futura.

## 35. S5-3 — Migração local e CT-01 no PostgreSQL

A origem Oracle respondeu a uma consulta em transação somente leitura e retornou 244 produtos na conferência inicial. Foi preparado um script para copiar as cinco tabelas a partir de uma leitura consistente do Oracle. No PostgreSQL, a carga exige o estado inicial da S5-2, preserva as chaves, compara as linhas e ajusta as sequências de identidade na mesma transação. A senha do destino é solicitada no terminal.

O CT-01 ganhou uma execução opcional com PostgreSQL, usando os mesmos cenários do SQLite e o conector PHP real em um esquema descartável. Para o PostgreSQL em `127.0.0.1`, os conectores PHP e Python preferem TLS e aceitam conexão por loopback se o servidor local estiver sem certificado. Endereços remotos continuam exigindo TLS.

**Status: concluída no ambiente local.** A carga foi confirmada após comparar os registros com o Oracle: 2 lojas, 244 produtos, 460 registros de preço, 13.444 eventos de coleta e 1 usuário. A suíte offline passou com 86 testes e 73 subtestes. A primeira tentativa do CT-01 no PostgreSQL parou antes dos cenários por acesso negado à pasta temporária padrão do pytest. A repetição em uma pasta temporária nova, sem repetir a carga, aprovou os três cenários do CT-01 em 6,94 segundos.

## 36. S5-4 — Preparação para hospedagem na Render

A Render foi escolhida como alternativa à VPS. A preparação usa Apache e PHP com `pdo_pgsql` em Docker, com `web/` como raiz pública e encaminhamento das páginas para o roteador existente. O serviço escuta na porta 10000. O cookie administrativo recebe `Secure` na Render, onde o HTTPS termina antes de a solicitação chegar ao PHP.

O PHP respondeu à home e ao login em uma simulação local do ambiente Render. O acesso a `/painel` sem sessão retornou `303` para `/login`, e o cookie apresentou `Secure`, `HttpOnly` e `SameSite=Strict`. A suíte offline passou com 86 testes e 73 subtestes.

**Status: em andamento.** Git sem commits ou remoto e Docker local indisponível para testar a imagem. A publicação, o PostgreSQL hospedado, a validação HTTPS e o domínio próprio continuam pendentes.
