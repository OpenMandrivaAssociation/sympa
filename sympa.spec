%define __noautoprov 'perl\(.*\)'
%define __noautoreq 'perl\\(Sympa.*\\)|perl\\(Archive\\)|perl\\(Auth\\)|perl\\(Bounce\\)|perl\\(Bulk\\)|perl\\(Commands\\)|perl\\(Conf\\)|perl\\(Config_XML\\)|perl\\(Datasource\\)|perl\\(Family\\)|perl\\(Fetch\\)|perl\\(Language\\)|perl\\(Ldap\\)|perl\\(List\\)|perl\\(Lock\\)|perl\\(Log\\)|perl\\(Marc.*\\)|perl\\(Message\\)|perl\\(PlainDigest\\)|perl\\(Robot\\)|perl\\(SharedDocument\\)|perl\\(Scenario\\)|perl\\(SQLSource\\)|perl\\(Task\\)|perl\\(Upgrade\\)|perl\\(WebAgent\\)'

Name:		sympa
Version:	6.1.5
Release:	5
Summary:	Electronic mailing list manager
License:	GPL
Group:		System/Servers
URL:		http://www.sympa.org/
Source0:	http://www.sympa.org/distribution/%{name}-%{version}.tar.gz
Source1:	%{name}.init
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
    --with-sendmail_aliases=%{_localstatedir}/lib/sympa/aliases
%make

%install
rm -rf %{buildroot}

%makeinstall_std HOST=localhost

# install our own init script
rm -rf %{buildroot}%{_sysconfdir}/sympa/rc.d
install -d -m 755 %{buildroot}%{_initrddir}
install -m 755 %{SOURCE1} %{buildroot}%{_initrddir}/%{name}

# apache conf
install -d -m 755 %{buildroot}%{_webappconfdir}
cat > %{buildroot}%{_webappconfdir}/sympa.conf <<EOF
Alias /static-sympa %{_localstatedir}/sympa/static_content
Alias /sympa %{_libdir}/sympa/cgi

<Directory %{_localstatedir}/sympa/static_content>
    Require all granted
</Directory>

<Directory %{_libdir}/sympa/cgi>
    Options ExecCGI
    AddHandler fastcgi-script .fcgi
    DirectoryIndex wwsympa-wrapper.fcgi

    Require all granted
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
%{_initrddir}/sympa

# binaries
%attr(-,sympa,sympa) %{_sbindir}/queue
%attr(-,sympa,sympa) %{_sbindir}/bouncequeue
%attr(-,sympa,sympa) %{_sbindir}/familyqueue
%attr(-,root,sympa) %{_sbindir}/aliaswrapper
%attr(-,root,sympa) %{_sbindir}/virtualwrapper
%{_sbindir}/sympa.pl
%{_sbindir}/alias_manager.pl
%{_sbindir}/archived.pl
%{_sbindir}/bounced.pl
%{_sbindir}/bulk.pl
%{_sbindir}/sympa_wizard.pl
%{_sbindir}/task_manager.pl

# other
%{_datadir}/sympa
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


%changelog
* Wed Jun 08 2011 Oden Eriksson <oeriksson@mandriva.com> 6.1.5-1mdv2011.0
+ Revision: 683163
- 6.1.5

* Sat Jan 22 2011 Guillaume Rousse <guillomovitch@mandriva.org> 6.1.4-1
+ Revision: 632256
- new version
- make mysql, postgresql and ldap optional dependencies of the init script (#62175)

* Mon Nov 15 2010 Nicolas Lécureuil <nlecureuil@mandriva.com> 6.1.3-1mdv2011.0
+ Revision: 597693
- Update to version 6.1.3

* Mon Oct 25 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.1.1-1mdv2011.0
+ Revision: 589265
- new version

* Sat Oct 02 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.1-0.beta7.2mdv2011.0
+ Revision: 582491
- patch0: robot_custome_parameter is not mandatory
- fix www interface configuration

* Wed Sep 29 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.1-0.beta7.1mdv2011.0
+ Revision: 582059
- new version

* Sat Jul 17 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.1-0.beta4.1mdv2011.0
+ Revision: 554584
- new version

* Sat May 29 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.0.2-1mdv2010.1
+ Revision: 546579
- new version (bugfix release)
- rework init script to make it more robust
- patch1: fix bulk daemon
- patch2: fix created directories ownership
- no need to explicitely add a group, %%_pre_useradd does it already
- split web interface in www subpackage, and use apache-independant dependencies (fix #59174)
- drop smrsh support, let expert sendmails users manage it themselves (fix #59173)
- don't run newalias if it doesn't exists (bug #59172)

  + Michael Scherer <misc@mandriva.org>
    - fix missing group issue, fix issue #59172

* Tue Apr 27 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.0.1-6mdv2010.1
+ Revision: 539525
- don't forget bulk module in init script

* Fri Apr 23 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.0.1-5mdv2010.1
+ Revision: 538361
- fix aliases on update, as queue and bouncequeue are now installed under %%{_sbindir}

* Sat Jan 23 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.0.1-4mdv2010.1
+ Revision: 495353
- no need for specific logrotate configuration anymore
- use standard 'mail' syslog facility, instead of a specific one, for sake of simplicity

* Tue Jan 19 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.0.1-3mdv2010.1
+ Revision: 493849
- rely on filetrigger for reloading apache configuration begining with 2010.1, rpm-helper macros otherwise
- switch to open to all by default, as the application does not allow modification of system state
- use installation patch submitted upstream

* Sat Jan 02 2010 Guillaume Rousse <guillomovitch@mandriva.org> 6.0.1-1mdv2010.1
+ Revision: 485176
- new version
- switch apache default access policy to open by default, as the application does not allow local modifications
- fix automatic dependencies

* Fri Dec 04 2009 Guillaume Rousse <guillomovitch@mandriva.org> 6.0-1mdv2010.1
+ Revision: 473475
- enforce new default access policy
- update to 6.0 final

* Fri Oct 09 2009 Oden Eriksson <oeriksson@mandriva.com> 6.0-0.b2.3mdv2010.0
+ Revision: 456333
- don't hardcode the buildhost host name at install

* Wed Sep 09 2009 Guillaume Rousse <guillomovitch@mandriva.org> 6.0-0.b2.2mdv2010.0
+ Revision: 434775
- fix dependencies

* Sun Aug 30 2009 Guillaume Rousse <guillomovitch@mandriva.org> 6.0-0.b2.1mdv2010.0
+ Revision: 422521
- new version
- spec cleanup, now than sympa installation process has been fixed upstream

* Sun Feb 15 2009 Guillaume Rousse <guillomovitch@mandriva.org> 5.4.6-1mdv2009.1
+ Revision: 340593
- new release

* Sun Jul 06 2008 Guillaume Rousse <guillomovitch@mandriva.org> 5.4.3-1mdv2009.0
+ Revision: 232181
- new version
- sync init script with mailman one
- use a single url prefix for all web stuff
- new version
- update install patch
- install cgi files under /var/www/sympa
- mysql dependency in init scrip

  + Pixel <pixel@mandriva.com>
    - adapt to %%_localstatedir now being /var instead of /var/lib (#22312)

* Mon Feb 18 2008 Thierry Vignaud <tv@mandriva.org> 5.3.4-2mdv2008.1
+ Revision: 171135
- rebuild
- fix "foobar is blabla" summary (=> "blabla") so that it looks nice in rpmdrake

* Wed Feb 06 2008 Guillaume Rousse <guillomovitch@mandriva.org> 5.3.4-1mdv2008.1
+ Revision: 163224
- new version

  + Olivier Blin <oblin@mandriva.com>
    - restore BuildRoot

  + Thierry Vignaud <tv@mandriva.org>
    - kill re-definition of %%buildroot on Pixel's request

* Thu Sep 06 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3.3-1mdv2008.0
+ Revision: 80909
- use new syslog rpm-helper
- new version

* Thu Jun 07 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3.1-1mdv2008.0
+ Revision: 36757
- new version
  fix monharc dependency capitalization

* Sun Jun 03 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3-1mdv2008.0
+ Revision: 34888
- final version

* Sun Jun 03 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3-0.beta4.2mdv2008.0
+ Revision: 34884
- new mandriva specific FHS-compliant init script

* Wed May 30 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3-0.beta4.1mdv2008.0
+ Revision: 32945
- new version


* Thu Mar 08 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3-0.beta1.2mdv2007.1
+ Revision: 134999
- don't remove aliases file on removal, just remove it from system aliases configuration, as mailman

* Wed Mar 07 2007 Guillaume Rousse <guillomovitch@mandriva.org> 5.3-0.beta1.1mdv2007.1
+ Revision: 134290
- use alias_database and alias_maps directives for postfix, so as to make newaliases command functionnal
- use get_free_syslog_facility helper script
- new version, using standard pre-release versionning scheme
- main configuration file is supposed to contains a password
- uses a patch instead of in-spec substitutions to handle installation, so as to fix insane perms also
- install wrappers setuid root

* Wed Nov 15 2006 Guillaume Rousse <guillomovitch@mandriva.org> 5.3a.10-1mdv2007.1
+ Revision: 84462
- attempt to migrate aliases automatically during upgrade
  use alias_database insteaf of alias_maps for postfix, as it allow to use sendmail-compatible newaliases command
- remove aliase database also on uninstallation
- fix listmaster adress substitution
- all sympa-created static web content is now created in %%_localstatedir/sympa/www
  change Apache alias from wws to sympa, for consistency with other webapps
- no need to create log file, syslog will do it alone
- fix syslog modification in %%preun
- fix alias removal during %%preun
- sanitize permissions
- sanitize setup a little bit:
- executables are in system standard directories (%%_bindir and %%_sbindir)
- samples are in documentation
- scripts are not samples
- sanitize macro use
- new version
- use a distinct alias file in /var/lib/sympa, and make sure it is included by MTA
- ship all documentation
- fix openssl path
- fix %%post
- LDAP support is optional
- move runtime-independant configuration change from %%post to %%install
- yet more cleanup
- ready-to-use static css directory
- fix %%post scriptlet
- put static web content (icons) into their own directory
- put messages files in correct place
- no need to add apache in sympa group, wwsympa is setuid
- useless verbosity
- don't install wrapper, wwsympa is setuid
- sanitize automatic configuration a little bit:
- dont use NIS domain name at all
- use hostname rather than domain name, as it is a safer default
- chain regexpes
- better regexp coherency
- correctly setup log facility in sympa configuration
- drop commented lines
- use herein document for README.urpmi
  more explicit instructions
- don't mess with mysql database creating script, as it breaks it
- use new webapps macros, allowing to discard versioned apache dependencies
  no need to requires mails-server during %%pre
- Import sympa

* Mon Jun 05 2006 Anne Nicolas <anicolas@mandriva.com> 5.2.1-1mdk
- new version, bug fix

* Wed May 17 2006 Anne Nicolas <anicolas@mandriva.com> 5.2-2mdk
- fix sympa.conf configuration for hostname

* Fri Apr 21 2006 Anne Nicolas <anicolas@mandriva.com> 5.2-1mdk
- update of translations
- performances optimization
- full virtual hosting support

* Sun Feb 05 2006 Anne Nicolas <anicolas@mandriva.com> 5.1.2-1mdk
- new version, bug fix

* Thu Sep 01 2005 Gwenole Beauchesne <gbeauchesne@mandriva.com> 5.1.0-2mdk
- buildrequires: perl-libintl-perl (Locale/Messages.pm)

* Sun Aug 28 2005 Anne Nicolas <anicolas@mandrakesoft.com> 5.1.0-1mdk
- new version
- add perl-Template require
- modify configure adding --with-docdir
- modify Makefile searching

* Thu Jul 14 2005 Guillaume Rousse <guillomovitch@mandriva.org> 4.1.5-2mdk 
- new mail-server requires
- new apache setup
- new apache macros
- use herein documents instead of additional sources
- ship sendmail secure shell link instead of managing it through post-installation procedure
- spec cleanup
- use %%mkrel

* Sat Feb 26 2005 Anne Nicolas <anicolas@mandrakesoft.com> 4.1.5-1mdk
- new version

* Fri Feb 18 2005 Oden Eriksson <oeriksson@mandrakesoft.com> 4.1.4-2mdk
- spec file cleanups, remove the ADVX-build stuff
- strip away annoying ^M

* Thu Feb 10 2005 Anne Nicolas <anne@mandrakesoft.com> 4.1.4-1mdk
- new version because of bug in web interface

* Tue Feb 08 2005 Anne Nicolas <anne@mandrakesoft.com> 4.1.3-1mdk
- new version (last one for this branch)

* Mon Nov 01 2004 Michael Scherer <misc@mandrake.org> 4.1.2-5mdk
- Buildrequires perl-MailTools

* Sat Oct 23 2004 Anne Nicolas <anne@mandrake.org> 4.1.2-4mdk
- use README.urpmi feature (thanks to rgs and misc)

* Sat Oct 23 2004 Anne Nicolas <anne@mandrake.org> 4.1.2-3mdk
- fix bug in mysql database creation script
- add comment about database creation at the end of install

* Thu Aug 05 2004 Anne Nicolas <anne@mandrake.org> 4.1.2-2mdk
- create sympa directory in /var/log for sympa's logs
- modify syslog : log all priorities in /var/log/sympa/sympa.log

* Thu Jul 08 2004 Anne Nicolas <anne@mandrake.org> 4.1.2-1mdk
- add apache configuration for wws
- remove patch for init file
- new version

* Sat Apr 24 2004 Anne Nicolas <anne@mandrake.org> 4.1.1-3mdk
- add SympaTransport exception
- add require perl-MailTools

* Fri Apr 23 2004 Olivier Blin <blino@mandrake.org> 4.1.1-2mdk
- merge changelog from the real 3.4.4.3-4mdk release to let the package be uploaded again (after a three months break)

* Thu Apr 22 2004 Guillaume Rousse <guillomovitch@mandrake.org> 4.1.1-1mdk
- new version, by popular demand (you know who you are)
- no more explicit perl dependencies, let spec-helper do its job

* Thu Apr 08 2004 Guillaume Rousse <guillomovitch@mandrake.org> 3.4.4.3-5mdk
- fixed multiple groups handling when adding sympa to apache group (Francis Muguet <muguet@ensta.fr>)
- requires mod_fastcgi and install cgi in correct dir (Guillaume Sauvenay <sauvenay@ccr.jussieu.fr>)
- user rpm-helper facility to create empty files

