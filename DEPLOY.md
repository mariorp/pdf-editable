# Despliegue · PDF Vencimientos Editable

## Servidor (45.84.209.235)

```bash
# 1. Copiar archivos
scp -r pdf_editable/ root@45.84.209.235:/opt/pdf-editable/

# 2. Instalar dependencias
cd /opt/pdf-editable
pip install -r requirements.txt

# 3. Lanzar como servicio systemd
cat > /etc/systemd/system/pdf-editable.service << 'EOF'
[Unit]
Description=H&A PDF Vencimientos Editable
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/pdf-editable
ExecStart=streamlit run app.py --server.port 8502 --server.address 127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pdf-editable
systemctl start pdf-editable
```

## Nginx (añadir al vhost existente)

```nginx
location /pdf-editable/ {
    proxy_pass         http://127.0.0.1:8502/;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade $http_upgrade;
    proxy_set_header   Connection "upgrade";
    proxy_set_header   Host $host;
}
```

Acceso: https://herrero.app/pdf-editable/
