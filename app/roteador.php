<?php
declare(strict_types=1);

// Roteador do servidor local: php -S 127.0.0.1:8080 -t web app/roteador.php
$caminho = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
header('X-Content-Type-Options: nosniff');

if (in_array($caminho, ['/login', '/painel', '/logout'], true)) {
    require __DIR__ . '/painel.php';
    return true;
}

$home = in_array($caminho, ['/', '/index.html'], true);
if ($home || in_array($caminho, ['/explorar', '/favoritos', '/sobre', '/privacidade', '/criar-conta', '/recuperar-senha', '/produto.html'], true)) {
    header('Content-Type: text/html; charset=UTF-8');
    header('Cache-Control: no-store');
    header("Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
    if ($home) {
        readfile(dirname(__DIR__) . '/web/index.html');
    } else {
        require __DIR__ . '/paginas.php';
    }
    return true;
}

if ($caminho === '/api/produtos') {
    require dirname(__DIR__) . '/web/api/produtos.php';
    return true;
}

if (in_array($caminho, [
    '/app.js', '/style.css', '/home.css', '/api/produtos.php', '/api/produto.php',
    '/produto.js', '/explorar.js', '/favoritos.js', '/paginas.css', '/vendor/chart.umd.min.js',
], true)) {
    return false; // O servidor entrega o arquivo estático ou executa o endpoint PHP.
}

http_response_code(404);
header('Content-Type: text/plain; charset=UTF-8');
echo 'Página não encontrada';
return true;
