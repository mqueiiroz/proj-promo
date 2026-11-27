<nav class="trilha-produto" aria-label="Navegação da oferta"><a class="acao-secundaria" href="/explorar">Explorar ofertas</a></nav>
<p id="estado-produto" role="status">Carregando produto…</p>
<div id="detalhes" class="detalhes"></div>
<div class="produto-paineis">
    <section id="comparar-lojas" class="painel-claro" hidden>
        <h2>Comparar lojas</h2>
        <div id="oferta-loja"></div>
        <p class="aviso-preco">O preço pode ter mudado na loja.</p>
    </section>
    <section id="historico" class="mensagem historico painel-claro" hidden>
        <h2>Histórico de preços</h2>
        <p id="estado-historico" hidden></p>
        <div id="grafico" class="grafico" hidden>
            <canvas id="grafico-precos" role="img" aria-label="Evolução dos preços registrados"></canvas>
        </div>
        <details id="registros" hidden>
            <summary>Ver registros de preço</summary>
            <table aria-label="Registros de preço">
                <thead><tr><th scope="col">Data e hora</th><th scope="col">Preço</th></tr></thead>
                <tbody id="precos-registrados"></tbody>
            </table>
        </details>
    </section>
</div>
<noscript><p>Ative o JavaScript para carregar o produto e seu histórico.</p></noscript>
