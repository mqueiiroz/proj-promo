"use strict";

const chaveFavoritos = "radar-hardware-favoritos";
const idFavoritoValido = id => /^[1-9][0-9]{0,37}$/.test(id);

function lerFavoritos() {
    const dados = JSON.parse(localStorage.getItem(chaveFavoritos) || "{}");
    return Object.fromEntries(Object.entries(dados || {}).filter(([id, alvo]) =>
        idFavoritoValido(id) && (alvo === null || (Number.isFinite(alvo) && alvo > 0))
    ).slice(0, 30));
}

function alterarFavorito(id, alvo) {
    if (!idFavoritoValido(id)) throw new Error("Produto inválido.");
    const favoritos = lerFavoritos();
    if (alvo === undefined) {
        delete favoritos[id];
    } else {
        if (!Object.hasOwn(favoritos, id) && Object.keys(favoritos).length >= 30) {
            throw new Error("Você pode salvar até 30 favoritos.");
        }
        favoritos[id] = alvo;
    }
    localStorage.setItem(chaveFavoritos, JSON.stringify(favoritos));
}

function criarControleFavorito(id) {
    const grupo = elemento("div", "controle-favorito", "");
    const botao = elemento("button", "home-botao", "Salvar nos favoritos");
    botao.type = "button";
    const estado = elemento("span", "", "");
    estado.setAttribute("role", "status");
    const atualizar = salvo => {
        botao.textContent = salvo ? "Remover dos favoritos" : "Salvar nos favoritos";
        botao.setAttribute("aria-pressed", String(salvo));
    };
    try {
        atualizar(Object.hasOwn(lerFavoritos(), id));
    } catch {
        botao.disabled = true;
    }
    botao.addEventListener("click", () => {
        try {
            const salvo = Object.hasOwn(lerFavoritos(), id);
            alterarFavorito(id, salvo ? undefined : null);
            atualizar(!salvo);
            estado.textContent = salvo ? "Favorito removido." : "Produto salvo neste navegador.";
        } catch (erro) {
            estado.textContent = erro.message === "Você pode salvar até 30 favoritos."
                ? erro.message : "Não foi possível atualizar os favoritos neste navegador.";
        }
    });
    grupo.append(botao, estado);
    return grupo;
}

async function carregarFavoritos(lista) {
    const estado = document.getElementById("estado-favoritos");
    try {
        const favoritos = Object.entries(lerFavoritos());
        if (!favoritos.length) {
            estado.textContent = "Nenhum favorito salvo. Abra os detalhes de uma oferta para salvar o produto.";
            return;
        }
        const linhas = await Promise.all(favoritos.map(async ([id, alvo]) => {
            let produto;
            try {
                const resposta = await fetch(`/api/produto.php?id=${id}`, {
                    signal: AbortSignal.timeout(15000),
                });
                if (!resposta.ok) throw new Error("Oferta indisponível.");
                produto = { ...(await resposta.json()).produto, id };
            } catch {
                produto = null;
            }
            return criarLinhaFavorito(id, alvo, produto);
        }));
        lista.replaceChildren(...linhas);
        estado.hidden = true;
    } catch {
        estado.textContent = "Não foi possível acessar os favoritos neste navegador.";
    }
}

function criarLinhaFavorito(id, alvo, produto) {
    const linha = elemento("article", "favorito-linha", "");
    const card = produto ? criarCard(produto) : elemento("div", "painel-claro", `Produto ${id} temporariamente indisponível.`);
    const painel = elemento("section", "painel-claro", "");
    const titulo = elemento("h2", "", "Alerta de preço");
    const estado = elemento("p", "", "");
    estado.setAttribute("role", "status");
    const formulario = elemento("form", "favorito-form", "");
    const rotulo = elemento("label", "sr-only", "Preço-alvo em reais");
    rotulo.htmlFor = `alvo-${id}`;
    const campo = elemento("input", "", "");
    Object.assign(campo, { id: `alvo-${id}`, type: "number", min: "0.01", step: "0.01", required: true, value: alvo ?? "" });
    campo.placeholder = "Preço-alvo em reais";
    const salvar = elemento("button", "home-botao", "Salvar alerta");
    salvar.type = "submit";
    const remover = elemento("button", "acao-secundaria", "Remover favorito");
    remover.type = "button";
    const mostrarAlvo = valor => {
        estado.textContent = valor === null ? "" : `Preço-alvo salvo: ${formatoPreco.format(valor)}`;
        if (valor !== null && produto?.disponivel && produto.preco != null && Number(produto.preco) <= valor) {
            estado.textContent += " · Preço atingido";
        }
    };
    mostrarAlvo(alvo);
    formulario.addEventListener("submit", evento => {
        evento.preventDefault();
        const valor = Number(campo.value);
        if (!Number.isFinite(valor) || valor <= 0) return;
        try {
            alterarFavorito(id, valor);
            mostrarAlvo(valor);
        } catch {
            estado.textContent = "Não foi possível salvar o alerta.";
        }
    });
    remover.addEventListener("click", () => {
        try {
            alterarFavorito(id, undefined);
            const lista = linha.parentElement;
            linha.remove();
            if (!lista.children.length) carregarFavoritos(lista);
        } catch {
            estado.textContent = "Não foi possível remover o favorito.";
        }
    });
    formulario.append(rotulo, campo, salvar);
    painel.append(titulo, elemento("p", "", "Confira aqui se a última coleta atingiu seu preço-alvo."), formulario, estado, remover);
    linha.append(card, painel);
    return linha;
}

const listaFavoritos = document.getElementById("favoritos-lista");
if (listaFavoritos) carregarFavoritos(listaFavoritos);
