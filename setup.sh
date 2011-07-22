mkdir -p ~/Code/sites/conf
echo "Include /Users/zeebo/Code/sites/conf/*.conf" >> /etc/apache2/httpd.conf
sed -iBAK "s/Listen 80/Listen 8080/" /etc/apache2/httpd.conf
sed -iBAK "s/#LoadModule php5_module/LoadModule php5_module/" /etc/apache2/httpd.conf

rndc-confgen -p 54 -b 256 > /etc/rndc.conf
head -n5 /etc/rndc.conf | tail -n4 > /etc/rndc.key
launchctl load /System/Library/LaunchDaemons/org.isc.named.plist

cp dev.zone /var/named/dev.zone
cat dev.named.conf >> /etc/named.conf
rndc reload

cp com.okco.router.plist /Library/LaunchDaemons/
launchctl load /Library/LaunchDaemons/com.okco.router.plist