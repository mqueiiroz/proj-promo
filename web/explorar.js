"use strict";

const buscaOfertas = document.getElementById("busca");
const filtroLoja = document.getElementById("filtro-loja");
const filtroFaixa = document.getElementById("faixa");
const filtroOrdem = document.getElementById("ordem");
let ofertasExploracao = [];

function textoParaBusca(texto) {
    return texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLocaleLowerCase("pt-BR");
}

function mostrarExploracao() {
    const busca = textoParaBusca(buscaOfertas.value.trim());
    const teto = filtroFaixa.value ? Number(filtroFaixa.value) : Infinity;
    const lista = ofertasExploracao.filter(produto =>
        textoParaBusca(produto.nome).includes(busca)
        && (!filtroLoja.value || produto.loja === filtroLoja.value)
        && Number(produto.preco) <= teto
    );
    if (filtroOrdem.value) {
        const direcao = filtroOrdem.value === "menor" ? 1 : -1;
        lista.sort((a, b) => direcao * (Number(a.preco) - Number(b.preco)));
    }
    document.getElementById("total-ofertas").textContent = lista.length === 1 ? "1 oferta" : `${lista.length} ofertas`;
    const produtos = document.getElementById("produtos");
    produtos.replaceChildren(...lista.map(produto => criarCard(produto)));
    if (lista.length === 0 && ofertasExploracao.length > 0) {
        produtos.append(elemento("p", "", "Nenhuma oferta corresponde aos filtros."));
    }
}

function atualizarExploracao(produtos) {
    ofertasExploracao = produtos;
    const selecionada = filtroLoja.value;
    const lojas = [...new Set(produtos.map(produto => produto.loja))].sort();
    filtroLoja.replaceChildren(...["", ...lojas].map(nome => {
        const opcao = elemento("option", "", nome || "Loja");
        opcao.value = nome;
        return opcao;
    }));
    filtroLoja.value = lojas.includes(selecionada) ? selecionada : "";
    mostrarExploracao();
}

buscaOfertas.addEventListener("input", mostrarExploracao);
[filtroLoja, filtroFaixa, filtroOrdem].forEach(filtro => filtro.addEventListener("change", mostrarExploracao));
filtroCategoria.addEventListener("change", () => {
    ofertasExploracao = [];
    mostrarExploracao();
    carregarProdutos(filtroCategoria.value);
});
carregarProdutos(filtroCategoria.value);
