const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function elemento(tag) {
    return {
        tag, children: [], hidden: false, textContent: "",
        append(...filhos) { this.children.push(...filhos); },
        replaceChildren(...filhos) { this.children = filhos; },
        setAttribute(chave, valor) { this[chave] = valor; },
        addEventListener() {},
    };
}

const { dados, esperado, detalhe } = JSON.parse(fs.readFileSync(0, "utf8"));
const elementos = Object.fromEntries(["estado", "produtos", "destaque", "categoria", "busca", "ordem", "total-ofertas"]
    .map(id => [id, elemento(id)]));
elementos.categoria.value = "";
elementos.busca.value = "";
elementos.ordem.value = "";
const contexto = vm.createContext({
    URL, Intl, AbortSignal, AbortController,
    document: { createElement: elemento, getElementById: id => elementos[id] },
    async fetch(url) {
        assert.equal(url, "/api/produtos.php");
        return { ok: true, json: async () => dados };
    },
});
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), contexto);
vm.runInContext(fs.readFileSync(path.join(path.dirname(process.argv[2]), "explorar.js"), "utf8"), contexto);
async function verificar() {
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(elementos.produtos.children.length, dados.produtos.length);
    assert.equal(elementos.destaque.hidden, !esperado);
    if (!esperado) {
        assert.equal(elementos.estado.children[0].textContent, "Nenhuma oferta disponível");
        return;
    }
    const [card] = elementos.produtos.children;
    assert.equal(card.children[1].children[0].href, dados.produtos[0].url_detalhes);
    const preco = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
    assert.equal(card.children[2].textContent, preco.format(esperado.preco));
    const loja = card.children.find(filho => filho.tag === "a");
    assert.equal(loja.href, esperado.afiliado);
    assert.match(loja.rel, /sponsored/);
    if (!detalhe) return;

    const ids = ["estado-produto", "detalhes", "historico", "estado-historico",
        "precos-registrados", "registros", "grafico", "grafico-precos"];
    const detalhes = Object.fromEntries(ids.map(id => [id, elemento(id)]));
    const graficos = [];
    const contextoProduto = vm.createContext({
        URL, Intl, AbortSignal,
        window: { location: { href: "http://localhost" + dados.produtos[0].url_detalhes } },
        document: {
            createElement: elemento,
            getElementById: id => detalhes[id],
            createDocumentFragment: () => elemento("fragmento"),
        },
        async fetch(url) {
            assert.equal(url, "/api/produto.php?id=" + esperado.id);
            return { ok: true, json: async () => detalhe };
        },
        Chart: class {
            constructor(_canvas, config) { graficos.push(config); }
        },
    });
    vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), contextoProduto);
    await vm.runInContext(fs.readFileSync(process.argv[3], "utf8"), contextoProduto);
    assert.equal(detalhes["estado-produto"].hidden, true);
    const pontos = graficos[0].data.datasets[0].data;
    assert.deepEqual(Array.from(pontos, ponto => ponto.y), [2399, 1899]);
    assert.equal(detalhes["precos-registrados"].children[0].children.length, 2);
}

verificar().catch(erro => {
    console.error(erro);
    process.exitCode = 1;
});
