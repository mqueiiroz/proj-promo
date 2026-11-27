<?php
declare(strict_types=1);

function origemPublica(): string
{
    return rtrim(getenv('RENDER_EXTERNAL_URL') ?: 'https://proj-promo.onrender.com', '/');
}

function imprimirMetadados(string $titulo, string $pagina, ?array $produto = null): void
{
    $descricao = match ($pagina) {
        '/' => 'Encontre ofertas de hardware da KaBuM! e acompanhe o histórico de preços no Radar Hardware.',
        '/explorar' => 'Busque e filtre ofertas de hardware por categoria, loja e faixa de preço.',
        '/favoritos' => 'Acompanhe seus produtos favoritos e compare os preços com os valores que você definiu.',
        '/sobre' => 'Entenda como o Radar Hardware coleta ofertas, registra preços e usa links de afiliado.',
        '/privacidade' => 'Saiba como o Radar Hardware usa cookies e armazenamento local e como entrar em contato.',
        '/produto' => 'Confira a oferta e o histórico de preços de ' . $produto['nome'] . ' no Radar Hardware.',
        default => null,
    };
    if ($descricao === null) {
        return;
    }

    $origem = origemPublica();
    $url = $origem . ($produto['url'] ?? $pagina);
    $imagemProduto = $produto['imagem'] ?? '';
    $temFoto = filter_var($imagemProduto, FILTER_VALIDATE_URL) !== false
        && parse_url($imagemProduto, PHP_URL_SCHEME) === 'https'
        && parse_url($imagemProduto, PHP_URL_USER) === null;
    $imagem = $temFoto ? $imagemProduto : $origem . '/compartilhar.png';
    $escapar = static fn (string $valor): string => htmlspecialchars($valor, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $openGraph = [
        'title' => $titulo . ' | Radar Hardware',
        'description' => $descricao,
        'type' => 'website',
        'url' => $url,
        'image' => $imagem,
        'image:alt' => $temFoto ? $produto['nome'] : 'Radar Hardware',
        'locale' => 'pt_BR',
        'site_name' => 'Radar Hardware',
    ];
    ?>
    <meta name="description" content="<?= $escapar($descricao) ?>">
    <link rel="canonical" href="<?= $escapar($url) ?>">
    <?php foreach ($openGraph as $propriedade => $valor): ?>
    <meta property="og:<?= $propriedade ?>" content="<?= $escapar($valor) ?>">
    <?php endforeach;
    if ($produto !== null) {
        $dados = [
            '@context' => 'https://schema.org',
            '@type' => 'Product',
            'name' => $produto['nome'],
            'url' => $url,
        ];
        if ($temFoto) {
            $dados['image'] = $imagemProduto;
        }
        if ($produto['preco'] !== null) {
            $dados['offers'] = [
                '@type' => 'Offer',
                'url' => $url,
                'price' => $produto['preco'],
                'priceCurrency' => 'BRL',
                'availability' => 'https://schema.org/' . ($produto['disponivel'] ? 'InStock' : 'OutOfStock'),
            ];
        }
        ?>
    <script type="application/ld+json"><?= json_encode($dados, JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE | JSON_THROW_ON_ERROR) ?></script>
        <?php
    }
}
