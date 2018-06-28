# Boya
Este proyecto surge por la necesidad de crear una boya científica donde recoger
datos de diferentes dispositivos. Para ello se ha optado por utilizar un minipc
modelo Raspeberry Pi 3 al cual se conectan los diferentes dispositivos.

Los datos recogidos son almacenados internamente en una base de datos, para 
posteriormente ser transmitidos a un servidor, en futuro será REDmic. Esta 
transmisión de datos se realiza mediante una conexión móvil 3g/4g.

## Dispositivos
* Estación meteorológica.
* Correntímetro.

## Conexión a internet




# DNS
Crear enlace simbólico en bin
```
sudo ln -s /home/boya/boya/dns.py /usr/bin/update_ip_dns
```

En el directorio /etc/network/if-up.d crear el siguiente script

```
#!/bin/sh
# Description:       Now that TCP/IP is configured, update my ip in
#                    server DNS
#

if [ "$IFACE" = usb0 ]; then
  echo "usb0 up" >> /var/log/usb0-uplog
fi

cmd="update_ip_dns"
eval $cmd
```

Le damos permisos de ejecución
```
sudo chmod +x update-ip
```