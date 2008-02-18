%define name	sympa
%define version 5.3.4
%define release %mkrel 2

# ugly...
%define exceptions perl(\\(Net::LDAP\\|Archive\\|Commands\\|Conf\\|Language\\|Ldap\\|List\\|Log\\|Marc.*\\|Message\\|SympaTransport\\|Version\\|X509\\|cookielib\\|mail\\|smtp\\|wwslib\\|.*\.pl\\))
%define _provides_exceptions %{exceptions}
%define _requires_exceptions %{exceptions}

Name:		%{name}
Version:	%{version}
Release:	%{release}
Summary:	Electronic mailing list manager
License:	GPL
Group:		System/Servers
Source0:	%{name}-%{version}.tar.gz
Source1:	%{name}.init
Patch0:     %{name}-5.3b.1-install.patch
URL:		http://www.sympa.org/
Requires:	openssl >= 0.9.5a
Requires:	mhonarc >= 2.4.5
Requires:	apache-mod_fastcgi
Requires:   mail-server
Requires:	perl-CGI-Fast
Requires:	perl-Crypt-CipherSaber
Requires:	perl-Template
Requires:	perl-MailTools
Requires(pre):	    rpm-helper
Requires(post):     rpm-helper >= 0.20.0
Requires(post):     mail-server
Requires(preun):    rpm-helper
Requires(preun):    mail-server
Requires(postun):   rpm-helper >= 0.16
BuildRequires:      rpm-helper >= 0.20.0
BuildRequires:      rpm-mandriva-setup >= 1.23
BuildRequires:	    openssl-devel >= 0.9.5a
BuildRequires:	    perl-MailTools
BuildRequires:	    perl-libintl-perl
BuildRoot:          %{_tmppath}/%{name}-%{version}

%description
SYMPA is an electronic mailing list manager. It is used to automate list
management functions such as subscription, moderation and management of 
archives. SYMPA also manages sending of messages to the lists, and 
makes it possible to reduce the load on the system. Provided that you 
have enough memory on your system, Sympa is especially well adapted for big 
lists. For a list with 20 000 subscribers, it takes 5 minutes to send a
message to 90% of subscribers, of course considering that the network is 
available.

Documentation is available under HTML and SGML (source) formats. 

%prep
%setup -q
%patch -p 1

%build
%serverbuild
./configure \
	--prefix=%{_localstatedir}/sympa \
	--with-mandir=%{_mandir} \
	--with-confdir=%{_sysconfdir}/sympa \
	--with-etcdir=%{_sysconfdir}/sympa \
	--with-cgidir=%{_var}/www/fcgi-bin \
	--with-iconsdir=%{_var}/www/sympa \
	--with-bindir=%{_bindir} \
	--with-sbindir=%{_sbindir} \
	--with-libexecdir=%{_bindir} \
	--with-libdir=%{_datadir}/sympa/lib \
	--with-datadir=%{_datadir}/sympa \
	--with-expldir=%{_localstatedir}/sympa/expl \
	--with-piddir=%{_var}/run/sympa \
	--with-localedir=%{_datadir}/locale \
	--with-scriptdir=%{_datadir}/sympa/script \
	--with-spooldir=%{_var}/spool/sympa \
	--with-initdir=%{_initrddir} \
    --with-docdir=%{_docdir}/%{name}-%{version} \
    --with-sampledir=%{_docdir}/%{name}-%{version}/sample

%make sources

%install
rm -rf %{buildroot}
%makeinstall_std

# Create bounce and archive incoming directories
for dir in bounce arc; do
  mkdir -p %{buildroot}%{_var}/spool/sympa/$dir
done

# Create bounce and archive storage directories
for dir in bounce arc www; do
  mkdir -p %{buildroot}%{_localstatedir}/sympa/$dir
done

# Create PID directory
mkdir -p %{buildroot}%{_var}/run/sympa

# log directory
mkdir -p %{buildroot}/%{_var}/log/sympa

# logrotate
install -d -m 755 %{buildroot}%{_sysconfdir}/logrotate.d
cat > %{buildroot}%{_sysconfdir}/logrotate.d/sympa <<EOF
%{_var}/log/sympa {
	missingok
	notifempty
	copytruncate
}
EOF

# init script
install -m 755 %{SOURCE1} %{buildroot}%{_initrddir}/%{name}

# sympa configuration
cat >> %{buildroot}%{_sysconfdir}/sympa/sympa.conf <<EOF
sendmail_aliases    %{_localstatedir}/sympa/aliases
EOF

perl -pi \
    -e 's|^#openssl(\s+).*|openssl$1%{_bindir}/openssl|;' \
    -e 's|^static_content_path(\s+).*|static_content_path$1%{_localstatedir}/sympa/www|;' \
    -e 's|^static_content_url(\s+).*|static_content_url$1/sympa-www|;' \
    %{buildroot}%{_sysconfdir}/sympa/sympa.conf

perl -pi \
    -e 's|^icons_url(\s+).*|icons_url$1/sympa-www/icons|;' \
    %{buildroot}%{_sysconfdir}/sympa/wwsympa.conf


# apache conf
install -d -m 755 %{buildroot}%{_webappconfdir}
cat > %{buildroot}%{_webappconfdir}/sympa.conf <<EOF
Alias /sympa-www/icons %{_var}/www/sympa
Alias /sympa-www %{_localstatedir}/sympa/www
ScriptAlias /sympa %{_var}/www/fcgi-bin/wwsympa.fcgi

<Directory "%{_var}/www/sympa">
    Allow from all
</Directory>

<Directory "%{_localstatedir}/sympa/www">
    Allow from all
</Directory>
EOF

cat > README.urpmi <<EOF
Mandriva RPM specific notes
---------------------------

Updates
-------
This new release:
- default /wws Apache URL is now /sympa, for consistency with other webapps
- binaries are now installed in standard system locations (%{_bindir} and
  %{_sbindir}), whereas they were previously installed under
  %%{_libdir}/sympa/bin. package update procedure should automatically correct
  %them in your alias file, but may eventually fails.

Setup
-----
The setup used here differs from default one, to achieve better FHS compliance.
- the binaries are in %{_bindir} and %{_sbindir}
- the configuration files are in %{_sysconfdir}/sympa
- the constant files are in %{_libdir}/sympa and %{_datadir}/sympa
- the variable files are in %{_localstatedir}/sympa
- the logs files are in %{_var}/log/sympa

Post-installation
-----------------
Sympa requires database for using the web interface. You have to create it
using the adequate script among %{_datadir}/sympa/script/db.

You can regenerate configuration files for sympa by executing
%{_sbindir}/sympa_wizard.pl

Additional useful packages
--------------------------
- perl-ldap for LDAP support
EOF

# sendmail secure shell
install -d -m 755 %{buildroot}%{_sysconfdir}/smrsh
ln -s %{_localstatedir}/sympa/bin/queue %{buildroot}%{_sysconfdir}/smrsh/sympa

# Delete documentation in wrong places
rm -f %{buildroot}%{_sysconfdir}/sympa/README
rm -f %{buildroot}%{_datadir}/sympa/README

# Install remaining documentation manually
install -m 644 COPYING README NEWS KNOWNBUGS README.urpmi %{buildroot}%{_docdir}/%{name}-%{version}

# don't install sudo wrapper, wwwsympa is setuid
rm -f %{buildroot}%{_var}/www/fcgi-bin/wwsympa_sudo_wrapper.pl

%find_lang sympa

%pre
%_pre_useradd sympa %{_localstatedir}/sympa /bin/false

%post
%_post_service sympa
%_post_webapp

if [ $1 = 1 ]; then
  # installation

  # Setup log facility for Sympa
  facility=`%_post_syslogadd %{_var}/log/sympa/sympa.log`

  # sympa configuration
  hostname=`hostname`

  perl -pi \
    -e "s|^domain(\s+).*|domain\$1$hostname|;" \
    -e "s|^listmaster(\s+).*|listmaster\$1listmaster\@$hostname|;" \
    -e "s|^wwsympa_url(\s+).*|wwsympa_url\$1http://$hostname/sympa|;" \
    -e "s|^syslog(\s+).*|syslog\$1$facility|;" \
    %{_sysconfdir}/sympa/sympa.conf

  # Initial aliase file creation
  cat >> %{_localstatedir}/sympa/aliases <<EOF
listmaster:	"|%{_bindir}/queue listmaster"
sympa:		"|%{_bindir}/queue sympa"
bounce+*:	"|%{_bindir}/bouncequeue sympa"
sympa-request:	listmaster@$hostname
sympa-owner:	listmaster@$hostname
EOF
  chown sympa.sympa %{_localstatedir}/sympa/aliases

  # mta-specific aliases inclusion procedure
  mta="`readlink /etc/alternatives/sendmail-command 2>/dev/null | cut -d . -f 2`"
  if [ "$mta" == "postfix" ]; then
    database=`/usr/sbin/postconf -h alias_database`
    maps=`/usr/sbin/postconf -h alias_maps`
    postconf -e \
        "alias_database = $database, hash:%{_localstatedir}/sympa/aliases" \
        "alias_maps = $maps, hash:%{_localstatedir}/sympa/aliases"
  else
    cat >> %{_sysconfdir}/aliases <<EOF
:include:	%{_localstatedir}/sympa/aliases
EOF
  fi
  /usr/bin/newaliases
else
  # find aliases file
  aliases=`awk '/sendmail_aliases/ {print $2}' %{_sysconfdir}/sympa/sympa.conf`
  if [ -z "$aliases" ]; then
    aliases=%{_sysconfdir}/aliases
  fi
  # correct pathes
  sed -i -e 's|%{_libdir}/sympa/bin|%{_bindir}|' $aliases
  # regenerate aliases
  /usr/bin/newaliases
fi

%preun
%_preun_service sympa

if [ $1 = 0 ]; then
  # uninstallation

  # clean syslog
  %_preun_syslogdel

  # remove aliases
  mta="`readlink /etc/alternatives/sendmail-command 2>/dev/null | cut -d . -f 2`"
  if [ "$mta" == "postfix" ]; then
    database=`/usr/sbin/postconf -h alias_database | \
      sed -e 's|, hash:%{_localstatedir}/sympa/aliases||'`
    maps=`/usr/sbin/postconf -h alias_maps | \
      sed -e 's|, hash:%{_localstatedir}/sympa/aliases||'`
    postconf -e \
      "alias_database = $database" \
      "alias_maps = $maps"
  else
    sed -i -e '/:include:   %{_localstatedir}/sympa/aliases/d' \
      %{_sysconfdir}/aliases
  fi
  /usr/bin/newaliases
fi

%postun
%_postun_userdel sympa
%_postun_webapp

%files -f sympa.lang
%defattr(-,root,root)

# variable directories
%attr(-,sympa,sympa) %{_localstatedir}/sympa
%attr(-,sympa,sympa) %{_var}/spool/sympa
%attr(-,sympa,sympa) %{_var}/run/sympa

# sympa config files
%dir %{_sysconfdir}/sympa
%config(noreplace) %attr(640,root,sympa) %{_sysconfdir}/sympa/sympa.conf
%config(noreplace) %{_sysconfdir}/sympa/wwsympa.conf
%{_sysconfdir}/sympa/create_list_templates
%{_sysconfdir}/sympa/scenari
%{_sysconfdir}/sympa/task_models
%{_sysconfdir}/sympa/web_tt2
%{_sysconfdir}/sympa/mail_tt2
%{_sysconfdir}/sympa/general_task_models

# various other configuration files
%{_sysconfdir}/smrsh/sympa
%{_initrddir}/sympa
%config(noreplace) %{_sysconfdir}/logrotate.d/sympa
%config(noreplace) %{_webappconfdir}/sympa.conf

# Binaries
%attr(-,sympa,sympa) %{_var}/www/fcgi-bin/wwsympa.fcgi
%attr(-,sympa,sympa) %{_var}/www/fcgi-bin/sympa_soap_server.fcgi
%attr(-,sympa,sympa) %{_bindir}/queue
%attr(-,sympa,sympa) %{_bindir}/bouncequeue
%attr(-,sympa,sympa) %{_bindir}/familyqueue
%attr(4750,root,sympa) %{_bindir}/aliaswrapper
%attr(4750,root,sympa) %{_bindir}/virtualwrapper
%{_sbindir}/*

# Data
%{_datadir}/sympa

# Logs
%{_var}/log/sympa

# Icons and binaries for Apache
%{_var}/www/sympa

# Documentation
%{_docdir}/%{name}-%{version}
%{_mandir}/man8/*

%clean
rm -rf %{buildroot}


