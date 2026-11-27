<?php
declare(strict_types=1);

// Roteador do servidor local: php -S 127.0.0.1:8080 -t web app/roteador.php
$caminho = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

if ($caminho === '/robots.txt' || $caminho === '/sitemap.xml') {
    require __DIR__ . '/rastreamento.php';
    return true;
}

if (in_array($caminho, ['/login', '/painel', '/logout'], true)) {
    require __DIR__ . '/painel.php';
    return true;
}

$idProduto = null;
if ($caminho === '/produto.html') {
    $idProduto = $_GET['id'] ?? null;
} elseif (preg_match('~\A/produto/([1-9][0-9]{0,37})(?:/[^/]+)?/?\z~', $caminho ?? '', $partes)) {
    $idProduto = $partes[1];
}
$home = in_array($caminho, ['/', '/index.html'], true);
if ($home || in_array($caminho, ['/explorar', '/produto.html'], true) || $idProduto !== null) {
    require_once __DIR__ . '/limite-publico.php';
    if (!limitarRequisicoesPublicas('paginas', 60)) {
        return true;
    }
}

if (is_string($idProduto) && preg_match('/\A[1-9][0-9]{0,37}\z/', $idProduto)) {
    ini_set('display_errors', '0');
    require __DIR__ . '/banco.php';
    require __DIR__ . '/produto-url.php';
    try {
        $consulta = conectarBanco()->prepare(
            'SELECT p.NOME, p.IMAGEM_URL, p.PRECO_ATUAL, p.DISPONIVEL
             FROM PRODUTO p JOIN LOJA l ON l.ID = p.LOJA_ID
             WHERE p.ID = CAST(:id AS DECIMAL(38, 0)) AND l.ATIVA = 1'
        );
        $consulta->execute(['id' => $idProduto]);
        $produto = $consulta->fetch();
    } catch (Throwable) {
        http_response_code(503);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Não foi possível carregar o produto. Tente novamente mais tarde.';
        return true;
    }
    if ($produto !== false) {
        $nomeProduto = $produto['NOME'];
        $urlProduto = urlProduto($idProduto, $nomeProduto);
        if ($caminho !== $urlProduto) {
            header('Location: ' . $urlProduto, true, 302);
            return true;
        }
        $produtoMeta = [
            'nome' => $nomeProduto,
            'url' => $urlProduto,
            'imagem' => $produto['IMAGEM_URL'],
            'preco' => $produto['PRECO_ATUAL'] === null ? null : (string) $produto['PRECO_ATUAL'],
            'disponivel' => (int) $produto['DISPONIVEL'] === 1,
        ];
        $caminho = '/produto';
    }
}

if ($home || isset($urlProduto) || in_array($caminho, ['/explorar', '/favoritos', '/sobre', '/privacidade', '/criar-conta', '/recuperar-senha'], true)) {
    header('Content-Type: text/html; charset=UTF-8');
    $cacheSegundos = match ($caminho) {
        '/', '/index.html', '/explorar', '/produto' => 300,
        '/sobre', '/privacidade' => 3600,
        default => null,
    };
    if ($cacheSegundos !== null && in_array($_SERVER['REQUEST_METHOD'] ?? 'GET', ['GET', 'HEAD'], true)) {
        header("Cache-Control: public, max-age={$cacheSegundos}, must-revalidate");
    }
    header("Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
    if ($home) {
        require_once __DIR__ . '/metadados.php';
        $html = file_get_contents(dirname(__DIR__) . '/web/index.html');
        ob_start();
        imprimirMetadados('Ofertas de hardware', '/');
        $metadados = ob_get_clean();
        echo str_replace('<!-- metadados -->', $metadados, $html);
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
    '/app.js', '/style.css', '/home.css', '/compartilhar.png', '/api/produtos.php', '/api/produto.php',
    '/produto.js', '/explorar.js', '/favoritos.js', '/paginas.css', '/vendor/chart.umd.min.js',
], true)) {
    return false; // O servidor entrega o arquivo estático ou executa o endpoint PHP.
}

http_response_code(404);
header('Content-Type: text/plain; charset=UTF-8');
echo 'Página não encontrada';
return true;
