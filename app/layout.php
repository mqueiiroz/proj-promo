<?php
declare(strict_types=1);

function abrirPagina(string $titulo, string $pagina, array $scripts = [], bool $autenticado = false): void
{
    $links = ['/' => 'Início', '/explorar' => 'Explorar ofertas', '/favoritos' => 'Favoritos e alertas'];
    ?>
<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= htmlspecialchars($titulo, ENT_QUOTES, 'UTF-8') ?> | Radar Hardware</title>
    <link rel="stylesheet" href="/style.css">
    <link rel="stylesheet" href="/home.css">
    <link rel="stylesheet" href="/paginas.css">
    <?php foreach ($scripts as $script): ?>
        <script src="<?= htmlspecialchars($script, ENT_QUOTES, 'UTF-8') ?>" defer></script>
    <?php endforeach; ?>
</head>
<body class="home paginas">
<header class="home-topo">
    <div class="home-largura home-barra">
        <a class="home-marca" href="/"><span aria-hidden="true">↘</span>Radar Hardware</a>
        <nav aria-label="Navegação principal">
            <?php foreach ($links as $url => $texto): ?>
                <a href="<?= $url ?>"<?= $pagina === $url ? ' aria-current="page"' : '' ?>><?= $texto ?></a>
            <?php endforeach; ?>
        </nav>
        <a class="home-botao home-entrar" href="<?= $autenticado ? '/painel' : '/login' ?>"><?= $autenticado ? 'Minha conta' : 'Entrar' ?></a>
    </div>
</header>
<main class="home-largura">
    <?php
}

function fecharPagina(): void
{
    ?>
</main>
<footer class="home-largura home-rodape">
    <span>Radar Hardware</span>
    <nav aria-label="Informações"><a href="/sobre">Sobre o projeto</a><a href="/privacidade">Privacidade</a></nav>
</footer>
</body>
</html>
    <?php
}
