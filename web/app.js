"use strict";

const formatoPreco = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function elemento(tag, classe, texto) {
    const node = document.createElement(tag);
    node.className = classe;
    node.textContent = texto;
    return node;
}

function linkSeguro(valor) {
    try {
        const url = new URL(valor);
        return url.protocol === "https:" && !url.username && !url.password
            && url.host === "www.kabum.com.br" && !url.search && !url.hash
            && /^\/produto\/[0-9]+(?:\/[^/?#]+)?\/?$/.test(url.pathname)
            ? url.href : null;
    } catch {
        return null;
    }
}

function linkAfiliadoSeguro(valor, urlOriginal) {
    try {
        const url = new URL(valor);
        const destino = linkSeguro(url.searchParams.get("ued"));
        const original = linkSeguro(urlOriginal);
        return url.protocol === "https:" && url.host === "www.awin1.com"
            && !url.username && !url.password && !url.hash && url.pathname === "/cread.php"
            && [...url.searchParams].length === 3
            && ["awinmid", "awinaffid", "ued"].every(chave => url.searchParams.getAll(chave).length === 1)
            && url.searchParams.get("awinmid") === "17729"
            && /^(?:0|[1-9][0-9]{0,19})$/.test(url.searchParams.get("awinaffid"))
            && destino !== null && destino === original ? url.href : null;
    } catch {
        return null;
    }
}

function linkDaLoja(produto, texto, classe = "") {
    const afiliado = linkAfiliadoSeguro(produto.url_afiliado, produto.url);
    const url = afiliado || linkSeguro(produto.url);
    if (!url) return null;

    const link = elemento("a", classe, texto);
    link.href = url;
    link.target = "_blank";
    link.rel = afiliado ? "sponsored noopener noreferrer" : "noopener noreferrer";
    link.append(elemento("span", "sr-only", " (abre em nova aba)"));
    return link;
}

const nomesCategorias = { CPU: "Processador", GPU: "Placa de vídeo", SSD: "SSD", RAM: "Memória RAM",
    FONTE: "Fonte de alimentação", COOLER: "Air cooler", WATER_COOLER: "Water cooler", GABINETE: "Gabinete", HD: "HD", PLACA_MAE: "Placa-mãe" };

function renderizarDestaque(area, produto) {
    if (!area) return;
    area.replaceChildren();
    area.hidden = !produto;
    if (!produto) return;

    const conteudo = elemento("div", "home-destaque-texto", "");
    const categoria = nomesCategorias[produto.categoria] || produto.categoria;
    conteudo.append(
        elemento("p", "home-destaque-categoria", `Oferta em destaque / ${categoria}`),
        elemento("h2", "", produto.nome),
        elemento("p", "home-destaque-preco", produto.preco == null
            ? "Preço não informado" : formatoPreco.format(Number(produto.preco))),
    );
    const acoes = elemento("div", "home-destaque-acoes", "");
    if (/^[1-9][0-9]{0,37}$/.test(produto.id)) {
        const detalhes = elemento("a", "home-botao", "Ver detalhes →");
        detalhes.href = `/produto.html?id=${produto.id}`;
        acoes.append(detalhes);
    }
    const loja = linkDaLoja(produto, "Ver na loja ↗", "home-destaque-loja");
    if (loja) acoes.append(loja);
    conteudo.append(acoes);

    const ilustracao = elemento("div", "home-destaque-ilustracao", "");
    ilustracao.setAttribute("aria-hidden", "true");
    const chip = elemento("div", "home-chip", "");
    chip.append(elemento("span", "", produto.categoria));
    ilustracao.append(chip);
    area.append(conteudo, ilustracao);
}

function criarCard(produto, titulo = "h2") {
    const card = elemento("article", "produto", "");
    const preco = produto.preco === null ? null : Number(produto.preco);
    const nome = elemento(titulo, "", produto.nome);
    if (titulo === "h2" && /^[1-9][0-9]{0,37}$/.test(produto.id)) {
        const detalhes = elemento("a", "link-detalhes", produto.nome);
        detalhes.href = `/produto.html?id=${produto.id}`;
        nome.textContent = "";
        nome.append(detalhes);
    }
    card.append(
        elemento("p", "categoria", `${produto.loja} · ${produto.categoria}`),
        nome,
        elemento("p", "preco", preco !== null && Number.isFinite(preco)
            ? formatoPreco.format(preco) : "Preço não informado"),
        elemento("p", `estoque${produto.disponivel ? " disponivel" : ""}`,
            produto.disponivel ? "Disponível na última coleta" : "Indisponível na última coleta")
    );
    const referencia = Number(produto.preco_referencia === undefined ? produto.preco_original : produto.preco_referencia);
    if (Number.isFinite(referencia) && preco > 0 && referencia > preco) {
        const historico = produto.origem_referencia === "historico";
        const rotulo = historico ? "Queda de preço · Menor preço nos 7 dias anteriores: "
            : produto.origem_referencia === "loja" ? "Promoção da loja · De " : "De ";
        const comparacao = elemento("p", "comparacao", rotulo);
        comparacao.append(elemento(historico ? "span" : "del", "", formatoPreco.format(referencia)));
        if (Number.isInteger(produto.desconto_pct) && produto.desconto_pct > 0) {
            comparacao.append(elemento("span", "desconto", `−${produto.desconto_pct}%`));
        }
        card.append(comparacao);
    }
    const link = linkDaLoja(produto, "Ver na loja ↗");
    if (link) card.append(link);
    return card;
}

let requisicaoAtual;

async function carregarProdutos(categoria = "") {
    const estado = document.getElementById("estado");
    const lista = document.getElementById("produtos");
    const destaque = document.getElementById("destaque");
    requisicaoAtual?.abort();
    const requisicao = new AbortController();
    requisicaoAtual = requisicao;
    lista.replaceChildren();
    estado.hidden = false;
    estado.setAttribute("role", "status");
    estado.replaceChildren(elemento("h2", "", "Carregando ofertas…"));
    try {
        const url = "/api/produtos.php" + (categoria ? `?categoria=${encodeURIComponent(categoria)}` : "");
        const resposta = await fetch(url, {
            headers: { Accept: "application/json" }, cache: "no-store",
            signal: AbortSignal.any([requisicao.signal, AbortSignal.timeout(15000)]),
        });
        if (!resposta.ok) throw new Error("Falha na API");
        const dados = await resposta.json();
        if (!Array.isArray(dados.produtos)) throw new Error("Resposta inválida");
        if (requisicao.signal.aborted) return;
        renderizarDestaque(destaque, dados.produtos[0]);
        if (typeof atualizarExploracao === "function") {
            atualizarExploracao(dados.produtos);
        } else {
            lista.replaceChildren(...dados.produtos.map(produto => criarCard(produto)));
        }
        if (dados.produtos.length === 0) {
            estado.replaceChildren(
                elemento("h2", "", "Nenhuma oferta disponível"),
                elemento("p", "", categoria
                    ? "Selecione outra categoria para conferir mais ofertas."
                    : "As ofertas aparecerão após a coleta identificar produtos com desconto.")
            );
        } else {
            estado.hidden = true;
        }
    } catch {
        if (requisicao.signal.aborted) return;
        renderizarDestaque(destaque);
        if (typeof atualizarExploracao === "function") atualizarExploracao([]);
        lista.replaceChildren();
        estado.setAttribute("role", "alert");
        estado.replaceChildren(
            elemento("h2", "", "Não foi possível carregar os produtos"),
            elemento("p", "", "Tente novamente mais tarde.")
        );
    }
}

const filtroCategoria = document.getElementById("categoria");
if (filtroCategoria && document.getElementById("destaque")) {
    filtroCategoria.addEventListener("change", () => carregarProdutos(filtroCategoria.value));
    carregarProdutos(filtroCategoria.value);
}
