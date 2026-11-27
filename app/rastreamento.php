<?php
declare(strict_types=1);

require_once __DIR__ . '/metadados.php';
$origem = origemPublica();

if ($caminho === '/robots.txt') {
    header('Content-Type: text/plain; charset=UTF-8');
    echo "User-agent: *\n";
    foreach (['/painel', '/login', '/logout', '/criar-conta', '/recuperar-senha', '/favoritos', '/api/'] as $rota) {
        echo "Disallow: {$rota}\n";
    }
    echo "\nSitemap: {$origem}/sitemap.xml\n";
    return;
}

ini_set('display_errors', '0');
require __DIR__ . '/banco.php';
require_once __DIR__ . '/produto-url.php';

$rotas = ['/', '/explorar', '/sobre', '/privacidade'];
try {
    $produtos = conectarBanco()->query(
        'SELECT p.ID, p.NOME FROM PRODUTO p JOIN LOJA l ON l.ID = p.LOJA_ID
         WHERE l.ATIVA = 1 ORDER BY p.ID'
    );
    foreach ($produtos as $produto) {
        $rotas[] = urlProduto((string) $produto['ID'], $produto['NOME']);
    }
} catch (Throwable) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Sitemap temporariamente indisponível.';
    return;
}

header('Content-Type: application/xml; charset=UTF-8');
echo "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
echo "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n";
foreach ($rotas as $rota) {
    $url = htmlspecialchars($origem . $rota, ENT_XML1 | ENT_QUOTES, 'UTF-8');
    echo "  <url><loc>{$url}</loc></url>\n";
}
echo "</urlset>\n";
