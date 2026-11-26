const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

const codigo = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const codigoExplorar = fs.readFileSync(path.join(__dirname, '../web/explorar.js'), 'utf8');
const codigoProduto = fs.readFileSync(path.join(__dirname, '../web/produto.js'), 'utf8');

// DOM mínimo para testar o comportamento do frontend sem dependências externas.
function node(tag = '') {
    return {
        tag, children: [], hidden: false, textContent: '',
        append(...items) { this.children.push(...items); },
        replaceChildren(...items) { this.children = items; },
        setAttribute(key, value) { this[key] = value; },
    };
}

async function executar(resposta, falha = false, consultar) {
    const estado = node();
    const produtos = node();
    const destaque = node();
    const busca = { value: '', addEventListener(_evento, callback) { this.alterar = callback; } };
    const ordem = { ...busca };
    const total = node();
    const categoria = {
        value: '',
        addEventListener(evento, callback) {
            assert.equal(evento, 'change');
            this.alterar = callback;
        },
    };
    const contexto = vm.createContext({
        URL, Intl, AbortSignal, AbortController,
        document: { createElement: node, getElementById: id => ({ estado, produtos, categoria, destaque, busca, ordem, 'total-ofertas': total })[id] },
        fetch: async (url, opcoes) => {
            if (consultar) return consultar(url, opcoes);
            assert.equal(url, '/api/produtos.php');
            if (falha) throw new Error('Falha de rede');
            return { ok: true, json: async () => resposta };
        },
    });
    vm.runInContext(codigo, contexto);
    vm.runInContext(codigoExplorar, contexto);
    await new Promise(resolve => setImmediate(resolve));
    return { estado, produtos, categoria, destaque, contexto, busca, ordem, total };
}

test('a home busca sem acentos e ordena o resultado por preço', async () => {
    const { produtos, busca, ordem, total } = await executar({ produtos: [
        { nome: 'Memória RAM A', preco: '200' },
        { nome: 'SSD', preco: '80' },
        { nome: 'Memória RAM B', preco: '100' },
    ] });
    busca.value = 'memoria';
    busca.alterar();
    ordem.value = 'menor';
    ordem.alterar();
    assert.deepEqual(Array.from(produtos.children, card => card.children[1].textContent),
        ['Memória RAM B', 'Memória RAM A']);
    assert.equal(total.textContent, '2 ofertas');
});

test('renderiza produto como texto e mantém os centavos', async () => {
    const { estado, produtos, contexto } = await executar({ produtos: [{
        nome: '<script>alert(1)</script>', loja: 'Kabum', categoria: 'SSD',
        preco: '1149.99', disponivel: true, url: 'https://www.kabum.com.br/produto/621162',
    }] });
    assert.equal(estado.hidden, true);
    const card = produtos.children[0];
    assert.equal(card.children[1].textContent, '<script>alert(1)</script>');
    assert.match(card.children[2].textContent, /1\.149,99/);
    assert.equal(card.children[4].rel, 'noopener noreferrer');
    assert.equal(vm.runInContext("linkSeguro('javascript:alert(1)')", contexto), null);
});

test('mostra estado vazio quando a API retorna lista vazia', async () => {
    const { estado, produtos } = await executar({ produtos: [] });
    assert.equal(estado.hidden, false);
    assert.equal(estado.children[0].textContent, 'Nenhuma oferta disponível');
    assert.equal(produtos.children.length, 0);
});

test('filtra pela API, descarta resposta atrasada e exibe preço original e desconto', async () => {
    const pendentes = new Map();
    const { categoria, estado, produtos } = await executar(null, false, (url, { signal }) => {
        if (url === '/api/produtos.php') return { ok: true, json: async () => ({ produtos: [] }) };
        return new Promise(resolve => pendentes.set(url, { resolve, signal }));
    });
    categoria.value = 'GPU';
    const gpu = categoria.alterar();
    categoria.value = 'SSD';
    const ssd = categoria.alterar();
    const anterior = pendentes.get('/api/produtos.php?categoria=GPU');
    assert.equal(anterior.signal.aborted, true);
    pendentes.get('/api/produtos.php?categoria=SSD').resolve({
        ok: true,
        json: async () => ({ produtos: [{
            nome: 'SSD de teste', loja: 'Kabum', categoria: 'SSD', preco: '100.00',
            preco_original: '125.00', desconto_pct: 20, disponivel: true,
        }] }),
    });
    await ssd;
    anterior.resolve({ ok: true, json: async () => ({ produtos: [] }) });
    await gpu;
    assert.equal(estado.hidden, true);
    const comparacao = produtos.children[0].children[4];
    assert.equal(comparacao.children[0].tag, 'del');
    assert.match(comparacao.children[0].textContent, /125,00/);
    assert.equal(comparacao.children[1].textContent, '−20%');
});

test('mostra mensagem genérica quando a requisição falha', async () => {
    const { estado, produtos } = await executar(null, true);
    assert.equal(estado.role, 'alert');
    assert.equal(estado.children[0].textContent, 'Não foi possível carregar os produtos');
    assert.equal(produtos.children.length, 0);
});

test('usa deeplink Awin válido do mesmo produto e identifica link patrocinado', async () => {
    const original = 'https://www.kabum.com.br/produto/621162';
    const afiliado = 'https://www.awin1.com/cread.php?' + new URLSearchParams({
        awinmid: '17729', awinaffid: '0', ued: original,
    });
    const { produtos } = await executar({ produtos: [{
        nome: 'SSD de teste', loja: 'Kabum', categoria: 'SSD', preco: '100.00',
        disponivel: true, url: original, url_afiliado: afiliado,
    }] });
    assert.equal(produtos.children[0].children[4].href, afiliado);
    assert.equal(produtos.children[0].children[4].rel, 'sponsored noopener noreferrer');
});

test('links de afiliado inválidos usam a URL original segura', async () => {
    const original = 'https://www.kabum.com.br/produto/621162';
    const base = 'https://www.awin1.com/cread.php?awinmid=17729&awinaffid=0&ued=';
    for (const afiliado of [null, 'javascript:alert(1)',
        base + encodeURIComponent('https://example.com/produto/621162'),
        base + encodeURIComponent('https://www.kabum.com.br/produto/999'),
        base.replace('17729', '999') + encodeURIComponent(original),
        base + encodeURIComponent(original) + '&awinaffid=123',
        base.replace('www.awin1.com', 'www.awin1.com.evil.example') + encodeURIComponent(original),
    ]) {
        const { produtos } = await executar({ produtos: [{
            nome: 'SSD', loja: 'Kabum', categoria: 'SSD', preco: '100.00',
            disponivel: true, url: original, url_afiliado: afiliado,
        }] });
        assert.equal(produtos.children[0].children[4].href, original);
    }
});

test('o título do card abre a página do produto', async () => {
    const { produtos } = await executar({ produtos: [{
        id: '42', nome: 'GPU de teste', loja: 'Kabum', categoria: 'GPU',
        url_detalhes: '/produto/42/gpu-de-teste',
        preco: '200.00', disponivel: true,
    }] });
    assert.equal(produtos.children[0].children[1].children[0].href, '/produto/42/gpu-de-teste');
});

test('o destaque usa a primeira oferta da API com os links reais de detalhes e loja', async () => {
    const url = 'https://www.kabum.com.br/produto/42';
    const oferta = { id: '42', nome: 'SSD de teste', categoria: 'SSD', preco: '250.15', url,
        url_detalhes: '/produto/42/ssd-de-teste' };
    const { destaque, produtos } = await executar({ produtos: [
        oferta, { ...oferta, id: '43', nome: 'Segunda oferta' },
    ] });
    const [texto] = destaque.children;
    assert.equal(destaque.hidden, false);
    assert.equal(texto.children[1].textContent, oferta.nome);
    assert.match(texto.children[2].textContent, /250,15/);
    assert.equal(texto.children[3].children[0].href, '/produto/42/ssd-de-teste');
    assert.equal(texto.children[3].children[1].href, url);
    assert.equal(produtos.children.length, 2);
});

async function executarDetalhe(historico) {
    const ids = [
        'estado-produto', 'detalhes', 'historico', 'estado-historico',
        'precos-registrados', 'registros', 'grafico', 'grafico-precos',
    ];
    const elementos = Object.fromEntries(ids.map(id => [id, { ...node(), hidden: id !== 'estado-produto' }]));
    const graficos = [];
    const contexto = vm.createContext({
        URL, Intl, AbortSignal,
        window: { location: { href: 'http://localhost/produto/42/ssd-de-teste' } },
        document: {
            getElementById: id => elementos[id],
            createElement: node,
            createDocumentFragment: () => node(),
        },
        fetch: async url => {
            assert.equal(url, '/api/produto.php?id=42');
            return { ok: true, json: async () => ({
                produto: {
                    nome: 'GPU de teste', loja: 'Kabum', categoria: 'GPU', preco: '200.05',
                    disponivel: true, url: 'https://www.kabum.com.br/produto/42',
                },
                historico,
            }) };
        },
        Chart: class {
            constructor(canvas, configuracao) { graficos.push({ canvas, configuracao }); }
        },
    });
    vm.runInContext(codigo, contexto);
    await vm.runInContext(codigoProduto, contexto);
    return { elementos, graficos };
}

test('preenche o gráfico e a tabela com os preços registrados e mantém o link da loja', async () => {
    const { elementos, graficos } = await executarDetalhe([
        { data: '2026-11-16 08:00:00', preco: '225.99' },
        { data: '2026-11-18 09:00:00', preco: '200.05' },
    ]);
    const card = elementos.detalhes.children[0];
    assert.equal(card.children[1].tag, 'h1');
    assert.equal(card.children[4].href, 'https://www.kabum.com.br/produto/42');
    const pontos = graficos[0].configuracao.data.datasets[0].data;
    assert.equal(pontos[0].x, Date.UTC(2026, 10, 16, 8));
    assert.equal(pontos[0].y, 225.99);
    assert.equal(pontos[1].y, 200.05);
    assert.equal(elementos.registros.hidden, false);
    assert.match(elementos['precos-registrados'].children[0].children[1].children[1].textContent, /200,05/);
});

test('exibe mensagem quando o produto não tem histórico', async () => {
    const { elementos, graficos } = await executarDetalhe([]);
    assert.equal(graficos.length, 0);
    assert.equal(elementos.grafico.hidden, true);
    assert.match(elementos['estado-historico'].textContent, /não há preços registrados/);
});
