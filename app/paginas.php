<?php
declare(strict_types=1);

require __DIR__ . '/layout.php';
$titulos = [
    '/explorar' => 'Explorar ofertas', '/favoritos' => 'Favoritos e alertas',
    '/sobre' => 'Sobre o projeto', '/privacidade' => 'Privacidade',
    '/criar-conta' => 'Criar conta', '/recuperar-senha' => 'Recuperar senha',
    '/produto' => $nomeProduto ?? 'Detalhes do produto',
];
$scripts = match ($caminho) {
    '/explorar' => ['/app.js', '/explorar.js'],
    '/favoritos' => ['/app.js', '/favoritos.js'],
    '/produto' => ['/app.js', '/vendor/chart.umd.min.js', '/favoritos.js', '/produto.js'],
    default => [],
};
abrirPagina($titulos[$caminho], $caminho, $scripts);
?>
<?php if ($caminho === '/explorar'): ?>
    <h1>Explorar ofertas</h1>
    <div class="explorar-filtros">
        <label class="sr-only" for="busca">Buscar por produto ou modelo</label>
        <input id="busca" type="search" placeholder="Buscar por produto ou modelo…">
        <div class="explorar-seletores">
            <label class="sr-only" for="categoria">Categoria</label>
            <select id="categoria"><option value="">Categoria</option><option value="CPU">Processadores</option><option value="GPU">Placas de vídeo</option><option value="SSD">SSDs</option><option value="RAM">Memórias RAM</option><option value="FONTE">Fontes de alimentação</option><option value="COOLER">Air coolers</option><option value="WATER_COOLER">Water coolers</option><option value="GABINETE">Gabinetes</option><option value="HD">HDs</option><option value="PLACA_MAE">Placas-mãe</option></select>
            <label class="sr-only" for="filtro-loja">Loja</label>
            <select id="filtro-loja"><option value="">Loja</option></select>
            <label class="sr-only" for="faixa">Faixa de preço</label>
            <select id="faixa"><option value="">Faixa de preço</option><option value="500">Até R$ 500</option><option value="1000">Até R$ 1.000</option><option value="2000">Até R$ 2.000</option></select>
            <label class="sr-only" for="ordem">Ordenar ofertas</label>
            <select id="ordem"><option value="">Maior desconto</option><option value="menor">Menor preço</option><option value="maior">Maior preço</option></select>
        </div>
    </div>
    <h2 id="total-ofertas" aria-live="polite">Ofertas</h2>
    <div id="estado" class="mensagem" role="status">Carregando ofertas…</div>
    <div id="produtos" class="produtos"></div>
<?php elseif ($caminho === '/favoritos'): ?>
    <h1>Favoritos e alertas</h1>
    <p id="estado-favoritos" role="status">Carregando favoritos…</p>
    <div id="favoritos-lista"></div>
<?php elseif ($caminho === '/sobre'): ?>
    <h1>Sobre o projeto</h1>
    <section class="painel-claro">
        <h2>Como as ofertas aparecem</h2>
        <p>O Radar Hardware reúne descontos registrados na KaBuM! e identifica a loja que vende cada oferta. O preço e a disponibilidade podem mudar entre a coleta e a sua visita.</p>
    </section>
    <section class="painel-claro">
        <h2>Como ler o histórico</h2>
        <p>O gráfico mostra os preços registrados e a data de cada mudança. A tabela abaixo dele detalha os valores e horários.</p>
    </section>
<?php elseif ($caminho === '/privacidade'): ?>
    <h1>Privacidade</h1>
    <section class="painel-claro">
        <h2>Dados da conta</h2>
        <p>As contas administrativas armazenam o e-mail e o hash da senha. O painel usa um cookie de sessão para manter o acesso autenticado.</p>
    </section>
    <section class="painel-claro">
        <h2>Preferências de alerta</h2>
        <p>Favoritos e preços-alvo ficam neste navegador. Você pode removê-los na tela de favoritos ou limpar os dados do site no navegador.</p>
    </section>
<?php elseif ($caminho === '/produto'): ?>
    <?php require __DIR__ . '/detalhes-pagina.php'; ?>
<?php else: ?>
    <section class="cartao-conta">
        <h1><?= $titulos[$caminho] ?></h1>
        <?php if ($caminho === '/criar-conta'): ?>
            <p>O cadastro público ainda está indisponível. As contas administrativas são cadastradas pelo responsável pelo projeto.</p>
            <fieldset class="formulario-painel conta-indisponivel" disabled>
                <legend class="sr-only">Cadastro indisponível</legend>
                <label for="cadastro-nome">Nome</label><input id="cadastro-nome" type="text">
                <label for="cadastro-email">E-mail</label><input id="cadastro-email" type="email">
                <label for="cadastro-senha">Senha</label><input id="cadastro-senha" type="password">
                <button class="home-botao" type="button">Criar conta</button>
            </fieldset>
        <?php else: ?>
            <p>A recuperação por e-mail ainda está indisponível. Para recuperar o acesso administrativo, fale com o responsável pelo projeto.</p>
            <fieldset class="formulario-painel conta-indisponivel" disabled>
                <legend class="sr-only">Recuperação indisponível</legend>
                <label for="recuperacao-email">E-mail</label><input id="recuperacao-email" type="email">
                <button class="home-botao" type="button">Enviar link por e-mail</button>
            </fieldset>
        <?php endif; ?>
        <p><a class="acao-secundaria" href="/login">← Voltar para entrar</a></p>
    </section>
<?php endif; ?>
<?php fecharPagina(); ?>
