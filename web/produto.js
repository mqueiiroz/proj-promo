"use strict";

// O Oracle devolve a data local gravada, sem fuso. UTC preserva esse horário
// na escala do gráfico e na formatação, independentemente do fuso do navegador.
const formatoDataColeta = new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short", timeStyle: "medium", timeZone: "UTC",
});
const formatoDiaColeta = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });
const meioDiaMs = 12 * 60 * 60 * 1000;

function exibirHistorico(historico) {
    const secao = document.getElementById("historico");
    const mensagem = document.getElementById("estado-historico");
    secao.hidden = false;
    if (historico.length === 0) {
        mensagem.textContent = "Ainda não há preços registrados para este produto.";
        mensagem.hidden = false;
        return;
    }

    const pontos = historico.map(registro => ({
        x: Date.parse(registro.data.replace(" ", "T") + "Z"),
        y: Number(registro.preco),
    }));
    const linhas = document.createDocumentFragment();
    for (const ponto of pontos) {
        const linha = document.createElement("tr");
        linha.append(
            elemento("td", "", formatoDataColeta.format(ponto.x)),
            elemento("td", "", formatoPreco.format(ponto.y)),
        );
        linhas.append(linha);
    }
    document.getElementById("precos-registrados").append(linhas);
    document.getElementById("registros").hidden = false;

    const grafico = document.getElementById("grafico");
    const instanteUnico = pontos[0].x === pontos[pontos.length - 1].x;
    try {
        grafico.hidden = false;
        new Chart(document.getElementById("grafico-precos"), {
            type: "line",
            data: {
                datasets: [{
                    label: "Preço registrado",
                    data: pontos,
                    borderColor: "#8ae2c0",
                    backgroundColor: "#8ae2c0",
                    pointRadius: pontos.length === 1 ? 5 : 3,
                }],
            },
            options: {
                maintainAspectRatio: false,
                animation: false,
                color: "#e6edf5",
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: {
                        title: itens => formatoDataColeta.format(itens[0].parsed.x),
                        label: item => formatoPreco.format(item.parsed.y),
                    } },
                },
                scales: {
                    x: {
                        type: "linear",
                        ...(instanteUnico ? {
                            min: pontos[0].x - meioDiaMs,
                            max: pontos[0].x + meioDiaMs,
                        } : {}),
                        grace: "5%",
                        ticks: {
                            color: "#4d6558",
                            maxTicksLimit: 5,
                            callback: valor => formatoDiaColeta.format(valor),
                        },
                    },
                    y: { ticks: { color: "#4d6558", callback: valor => formatoPreco.format(valor) } },
                },
            },
        });
    } catch {
        grafico.hidden = true;
        mensagem.textContent = "O gráfico está indisponível. Consulte os preços na tabela.";
        mensagem.hidden = false;
        document.getElementById("registros").open = true;
    }
}

function organizarDetalhes(card, produto, id) {
    const comparacao = document.getElementById("comparar-lojas");
    if (!comparacao) return;

    const loja = document.getElementById("oferta-loja");
    const dados = elemento("div", "loja-dados", "");
    dados.append(elemento("strong", "", produto.loja));
    for (const seletor of [".preco", ".data-atualizacao", ".comparacao", ".estoque"]) {
        const campo = card.querySelector(seletor);
        if (campo) dados.append(campo);
    }
    loja.append(dados);
    const link = card.querySelector(":scope > a");
    if (link) {
        link.classList.add("home-botao");
        loja.append(link);
    }
    comparacao.hidden = false;

    const ilustracao = elemento("div", "home-chip produto-chip", "");
    ilustracao.setAttribute("aria-hidden", "true");
    ilustracao.append(elemento("span", "", produto.categoria));
    const titulo = elemento("div", "produto-titulo", "");
    titulo.append(card.querySelector(".categoria"), card.querySelector("h1"));
    card.prepend(ilustracao, titulo);
    card.append(criarControleFavorito(id));
}

async function carregarProduto() {
    const estado = document.getElementById("estado-produto");
    const caminho = new URL(window.location.href).pathname;
    const id = caminho.match(/^\/produto\/([1-9][0-9]{0,37})\/[a-z0-9-]+$/)?.[1];
    if (!/^[1-9][0-9]{0,37}$/.test(id)) {
        estado.textContent = "Selecione um produto na página de promoções.";
        return;
    }

    try {
        const resposta = await fetch(`/api/produto.php?id=${id}`, {
            headers: { Accept: "application/json" },
            cache: "no-store",
            signal: AbortSignal.timeout(15000),
        });
        if (resposta.status === 404) {
            estado.textContent = "Produto não encontrado.";
            return;
        }
        if (!resposta.ok) throw new Error("Falha na API");
        const { produto, historico } = await resposta.json();
        const card = criarCard(produto, "h1");
        organizarDetalhes(card, produto, id);
        document.getElementById("detalhes").append(card);
        document.title = `${produto.nome} | Monitor de Hardware`;
        exibirHistorico(historico);
        estado.hidden = true;
    } catch {
        estado.setAttribute("role", "alert");
        estado.textContent = "Não foi possível carregar o produto. Tente novamente mais tarde.";
    }
}

carregarProduto();
