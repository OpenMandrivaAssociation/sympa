# disable linting for srpm. Sflo
%define _build_pkgcheck_srpm %{nil}
# the following definitions are badnes 50 each. Sflo
%define _provides_exceptions perl(.*)
%define _requires_exceptions perl(\\(Sympa.*\\|Archive\\|Auth\\|Bounce\\|Bulk\\|Commands\\|Conf\\|Config_XML\\|Datasource\\|Family\\|Fetch\\|Language\\|Ldap\\|List\\|Lock\\|Log\\|Marc.*\\|Message\\|PlainDigest\\|Robot\\|SharedDocument\\|Scenario\\|SQLSource\\|Task\\|Upgrade\\|WebAgent\\|SympaTransport\\`))

Name:		sympa
Version:	6.1.22
Release:	2
Summary:	Electronic mailing list manager
License:	GPL
Group:		System/Servers
URL:		http://www.sympa.org/
Source0:	http://www.sympa.org/distribution/%{name}-%{version}.tar.gz
Source1:	sympa.service
Source2:	sympa-bulk.service
Source3:	sympa-archived.service
Source4:	sympa-bounced.service
Source5:	sympa-task_manager.service
Requires:	openssl >= 0.9.5a
Requires:	mhonarc >= 2.4.5
Requires:   mail-server
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
BuildRequires:	    gettext-devel
BuildRequires:	    perl(HTML::StripScripts::Parser)

Provides:	    perl(SympaTransport)

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

%package www
Summary:	Web interface for %{name}
Group:		System/Servers
Requires:	%{name} = %{version}-%{release}
Requires:	webserver
Suggests:   apache-mod_fastcgi
Requires(post):     rpm-helper >= 0.20.0
Requires(postun):   rpm-helper >= 0.16

%description www
This package contains the web interface for %{name}.

%prep
%setup -q 

%build
%serverbuild
%configure2_5x \
    --enable-fhs \
    --libexecdir=%{_sbindir} \
    --sysconfdir=%{_sysconfdir}/sympa \
    --with-confdir=%{_sysconfdir}/sympa \
    --with-aliases_file=%{_localstatedir}/lib/sympa/aliases
%make

%install
rm -rf %{buildroot}

%makeinstall_std HOST=localhost

rm -f %{buildroot}%{_sysconfdir}/sympa/rc.d/init.d/sympa
install -D -m 644 %{SOURCE1} %{buildroot}%{_unitdir}/sympa.service
install -D -m 644 %{SOURCE2} %{buildroot}%{_unitdir}/sympa-bulk.service
install -D -m 644 %{SOURCE3} %{buildroot}%{_unitdir}/sympa-archived.service
install -D -m 644 %{SOURCE4} %{buildroot}%{_unitdir}/sympa-bounced.service
install -D -m 644 %{SOURCE5} %{buildroot}%{_unitdir}/sympa-task_manager.service

# apache conf
install -d -m 755 %{buildroot}%{_webappconfdir}
cat > %{buildroot}%{_webappconfdir}/sympa.conf <<EOF
Alias /static-sympa %{_localstatedir}/sympa/static_content
Alias /sympa %{_libdir}/sympa/cgi

<Directory %{_localstatedir}/sympa/static_content>
    Order allow,deny
    Allow from all
</Directory>

<Directory %{_libdir}/sympa/cgi>
    Options ExecCGI
    AddHandler fastcgi-script .fcgi
    DirectoryIndex wwsympa-wrapper.fcgi

    Order allow,deny
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
- the variable files are in %{_localstatedir}/lib/sympa
- the logs files are in %{_localstatedir}/log/sympa

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

# Install remaining documentation manually
install -m 644 COPYING README NEWS README.urpmi %{buildroot}%{_docdir}/%{name}

# don't install  bundled certs
rm -f %{buildroot}%{_datadir}/sympa/ca-bundle.crt

# not the place for documentation
rm -f %{buildroot}%{_sysconfdir}/sympa/README

%find_lang sympa
%find_lang web_help
cat web_help.lang >> sympa.lang

%clean
rm -rf %{buildroot}

%pre
%_pre_useradd sympa %{_localstatedir}/lib/sympa /bin/false

%post
%_post_service sympa

if [ $1 = 1 ]; then
  # installation

  # sympa configuration
  hostname=`hostname`

  perl -pi \
    -e "s|^domain(\s+).*|domain\$1$hostname|;" \
    -e "s|^listmaster(\s+).*|listmaster\$1listmaster\@$hostname|;" \
    -e "s|^wwsympa_url(\s+).*|wwsympa_url\$1http://$hostname/sympa|;" \
    -e "s|^syslog(\s+).*|syslog\$1mail|;" \
    %{_sysconfdir}/sympa/sympa.conf

  # Initial aliase file creation
  cat >> %{_localstatedir}/lib/sympa/aliases <<EOF
listmaster:	"|%{_sbindir}/queue listmaster"
sympa:		"|%{_sbindir}/queue sympa"
bounce+*:	"|%{_sbindir}/bouncequeue sympa"
sympa-request:	listmaster@$hostname
sympa-owner:	listmaster@$hostname
EOF
  chown sympa.sympa %{_localstatedir}/lib/sympa/aliases

  # mta-specific aliases inclusion procedure
  mta="`readlink /etc/alternatives/sendmail-command 2>/dev/null | cut -d . -f 2`"
  if [ "$mta" == "postfix" ]; then
    database=`/usr/sbin/postconf -h alias_database`
    maps=`/usr/sbin/postconf -h alias_maps`
    postconf -e \
        "alias_database = $database, hash:%{_localstatedir}/lib/sympa/aliases" \
        "alias_maps = $maps, hash:%{_localstatedir}/lib/sympa/aliases"
  else
    cat >> %{_sysconfdir}/aliases <<EOF
:include:	%{_localstatedir}/lib/sympa/aliases
EOF
  fi
  # masqmail don't have this command
  [ -x /usr/bin/newaliases ] && /usr/bin/newaliases
else
  # find aliases file
  aliases=`awk '/sendmail_aliases/ {print $2}' %{_sysconfdir}/sympa/sympa.conf`
  if [ -z "$aliases" ]; then
    aliases=%{_sysconfdir}/aliases
  fi
  # correct pathes
  sed -i \
      -e 's|%{_bindir}/queue|%{_sbindir}/queue|' \
      -e 's|%{_bindir}/bouncequeue|%{_sbindir}/bouncequeue|' \
      $aliases
  # regenerate aliases
  /usr/bin/newaliases
fi

%post www
%if %mdkversion < 201010
%_post_webapp
%endif

%preun
%_preun_service sympa

if [ $1 = 0 ]; then
  # uninstallation

  # remove aliases
  mta="`readlink /etc/alternatives/sendmail-command 2>/dev/null | cut -d . -f 2`"
  if [ "$mta" == "postfix" ]; then
    database=`/usr/sbin/postconf -h alias_database | \
      sed -e 's|, hash:%{_localstatedir}/lib/sympa/aliases||'`
    maps=`/usr/sbin/postconf -h alias_maps | \
      sed -e 's|, hash:%{_localstatedir}/lib/sympa/aliases||'`
    postconf -e \
      "alias_database = $database" \
      "alias_maps = $maps"
  else
    sed -i -e '/:include:   %{_localstatedir}/lib/sympa/aliases/d' \
      %{_sysconfdir}/aliases
  fi
  /usr/bin/newaliases
fi

%postun
%_postun_userdel sympa

%postun www
%if %mdkversion < 201010
%_postun_webapp
%endif

%files -f sympa.lang
%defattr(-,root,root)
%{_docdir}/%{name}

# variable directories
%attr(-,sympa,sympa) %{_localstatedir}/lib/sympa
%attr(-,sympa,sympa) %{_localstatedir}/spool/sympa
%attr(-,sympa,sympa) %{_localstatedir}/run/sympa

# config files
%dir %{_sysconfdir}/sympa
%config(noreplace) %attr(640,root,sympa) %{_sysconfdir}/sympa/sympa.conf
%config(noreplace) %{_sysconfdir}/sympa/wwsympa.conf
%config(noreplace) %{_sysconfdir}/sympa/data_structure.version

%{_unitdir}/sympa.service
%{_unitdir}/sympa-bulk.service
%{_unitdir}/sympa-archived.service
%{_unitdir}/sympa-bounced.service
%{_unitdir}/sympa-task_manager.service

# binaries
%attr(-,sympa,sympa) %{_sbindir}/queue
%attr(-,sympa,sympa) %{_sbindir}/bouncequeue
%attr(-,sympa,sympa) %{_sbindir}/familyqueue
%attr(-,sympa,sympa) %{_sbindir}/sympa_newaliases.pl
%attr(-,root,sympa) %{_sbindir}/sympa_newaliases-wrapper
%{_sbindir}/sympa.pl
%{_sbindir}/alias_manager.pl
%{_sbindir}/archived.pl
%{_sbindir}/bounced.pl
%{_sbindir}/bulk.pl
%{_sbindir}/sympa_wizard.pl
%{_sbindir}/task_manager.pl

# other
%{_datadir}/sympa
%{_mandir}/man1/sympa_newaliases.1*
%{_mandir}/man8/*

%files www
%defattr(-,root,root)
%dir %{_libdir}/sympa
%dir %{_libdir}/sympa/cgi
%{_libdir}/sympa/cgi/wwsympa.fcgi
%{_libdir}/sympa/cgi/sympa_soap_server.fcgi
%attr(-,sympa,sympa) %{_libdir}/sympa/cgi/sympa_soap_server-wrapper.fcgi
%attr(-,sympa,sympa) %{_libdir}/sympa/cgi/wwsympa-wrapper.fcgi
%config(noreplace) %{_webappconfdir}/sympa.conf

