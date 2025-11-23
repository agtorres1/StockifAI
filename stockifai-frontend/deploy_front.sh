#!/bin/bash

echo "Instalando dependencias..."
npm install
echo "Building Angular production..."
npx ng build --configuration production

echo "Limpiando carpeta actual en /var/www/stockifai..."
sudo rm -rf /var/www/stockifai/*

echo "Copiando nuevo build..."
sudo cp -r dist/stockifai-frontend/* /var/www/stockifai/

echo "Otorgando permisos..."
sudo chown -R www-data:www-data /var/www/stockifai
sudo chmod -R 755 /var/www/stockifai

echo "Reiniciando nginx..."
sudo systemctl restart nginx

echo "Deploy completado!"
