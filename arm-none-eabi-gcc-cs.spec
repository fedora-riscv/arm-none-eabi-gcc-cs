# CodeSourcery releases are identified by a date, a release number,
# and a package number for downloading from their web site
%global cs_date        2013.11
%global cs_rel         24
%global cs_pkgnum      12189

%global processor_arch arm
%global target         %{processor_arch}-none-eabi
%global gcc_ver        4.8.1
%global gcc_short_ver  4.8

# we need newlib to compile complete gcc, but we need gcc to compile newlib,
# so compile minimal gcc first
%global bootstrap      0

Name:           %{target}-gcc-cs
Version:        %{cs_date}.%{cs_rel}
Release:        3%{?dist}
Summary:        GNU GCC for cross-compilation for %{target} target
Group:          Development/Tools

# Most of the sources are licensed under GPLv3+ with these exceptions:
# LGPLv2+ libquadmath/ libjava/libltdl/ gcc/testsuite/objc.dg/gnu-encoding/generate-random 
#         libgcc/soft-fp/ libffi/msvcc.sh
# LGPLv3+ gcc/prefix.c
# BSD libgo/go/regexp/testdata/testregex.cz zlib/example.c libffi/ 
#     libjava/classpath/external/relaxngDatatype/org/relaxng/datatype/helpers/DatatypeLibraryLoader.java
# GPLv2+ libitm/testsuite/libitm.c/memset-1.c libjava/
# Public Domain libjava/classpath/external/sax/org/xml/sax/ext/EntityResolver2.java
#               libjava/classpath/external/sax/org/xml/sax/ext/DeclHandler.java
# BSL zlib/contrib/dotzlib/DotZLib/GZipStream.cs
License:        GPLv2+ and GPLv3+ and LGPLv2+ and BSD
URL:            http://www.codesourcery.com/sgpp/lite/%{processor_arch}

#we don't use orignal tarball, because it's HUGE
Source0:        gcc-%{cs_date}-%{cs_rel}.tar.bz2
#Source0 origin:
#wget https://sourcery.mentor.com/GNUToolchain/package%{cs_pkgnum}/public/%{target}/%{processor_arch}-%{cs_date}-%{cs_rel}-%{target}.src.tar.bz2
#tar jxvf %{processor_arg}-%{cs_date}-%{cs_rel}-%{target}.src.tar.bz2

Source1:        README.fedora
Source2:        bootstrapexplain

BuildRequires:  %{target}-binutils >= 2.21, zlib-devel gmp-devel mpfr-devel libmpc-devel flex autogen
%if ! %{bootstrap}
BuildRequires:  %{target}-newlib
%endif
Requires:       %{target}-binutils >= 2.21
Provides:       %{target}-gcc = %{gcc_ver}

%description
This is a Cross Compiling version of GNU GCC, which can be used to
compile for the %{target} platform, instead of for the
native %{_arch} platform.

This package is based on the CodeSourcery %{cs_date}-%{cs_rel} release,
which includes improved ARM target support compared to the corresponding 
GNU GCC release.

%package c++
Summary:        Cross Compiling GNU GCC targeted at %{target}
Group:          Development/Languages
Requires:       %{name} = %{version}-%{release}
Provides:       %{target}-gcc-c++ = %{gcc_ver}

%description c++
This package contains the Cross Compiling version of g++, which can be used to
compile c++ code for the %{target} platform, instead of for the native 
%{_arch} platform.

This package is based on the CodeSourcery %{cs_date}-%{cs_rel} release,
which includes improved ARM target support compared to the corresponding 
GNU GCC release.

%prep
%setup -q -c
pushd gcc-%{gcc_short_ver}-%{cs_date}

contrib/gcc_update --touch
popd
cp -a %{SOURCE1} .

# Extract %%__os_install_post into os_install_post~
cat << \EOF > os_install_post~
%__os_install_post
EOF

# Generate customized brp-*scripts
cat os_install_post~ | while read a x y; do
case $a in
# Prevent brp-strip* from trying to handle foreign binaries
*/brp-strip*)
  b=$(basename $a)
  sed -e 's,find $RPM_BUILD_ROOT,find $RPM_BUILD_ROOT%_bindir $RPM_BUILD_ROOT%_libexecdir,' $a > $b
  chmod a+x $b
  ;;
esac
done

sed -e 's,^[ ]*/usr/lib/rpm.*/brp-strip,./brp-strip,' \
< os_install_post~ > os_install_post 


%build
mkdir -p gcc-%{target}
pushd gcc-%{target}
CC="%{__cc} ${RPM_OPT_FLAGS}" \
../gcc-%{gcc_short_ver}-%{cs_date}/configure --prefix=%{_prefix} --mandir=%{_mandir} --libdir=%{_libdir} \
  --with-pkgversion="Fedora %{version}-%{release}" \
  --with-bugurl="https://bugzilla.redhat.com/" \
  --enable-lto \
  --infodir=%{_infodir} --target=%{target} \
  --enable-interwork --enable-multilib --with-newlib \
%if %{bootstrap}
  --enable-languages=c --disable-nls --disable-shared --disable-threads --with-gnu-as --with-gnu-ld --with-gmp --with-mpfr --with-mpc --without-headers --with-system-zlib --disable-libssp
%else
  --enable-languages=c,c++ --disable-nls --disable-shared --disable-threads --with-gnu-as --with-gnu-ld --with-gmp --with-mpfr --with-mpc --with-newlib --with-headers=/usr/%{target}/include --with-system-zlib
%endif

# In general, building GCC is not smp-safe, but give it initial push anyway
%if %{bootstrap}
make all-gcc %{?_smp_mflags} || make all-gcc
%else
make %{?_smp_mflags} || make
%endif
popd


%install
pushd gcc-%{target}
%if %{bootstrap}
make install-gcc DESTDIR=$RPM_BUILD_ROOT
install -p -m 0755 -D %{SOURCE2} $RPM_BUILD_ROOT/%{_bindir}/%{target}-g++
install -p -m 0755 -D %{SOURCE2} $RPM_BUILD_ROOT/%{_bindir}/%{target}-c++
%else
make install DESTDIR=$RPM_BUILD_ROOT
%endif
popd
# we don't want these as we are a cross version
rm -r $RPM_BUILD_ROOT%{_infodir}
rm -r $RPM_BUILD_ROOT%{_mandir}/man7
rm -f $RPM_BUILD_ROOT%{_libdir}/libiberty.a
# and these aren't usefull for embedded targets
rm -r $RPM_BUILD_ROOT%{_prefix}/lib*/gcc/%{target}/%{gcc_ver}/install-tools ||:
rm -r $RPM_BUILD_ROOT%{_libexecdir}/gcc/%{target}/%{gcc_ver}/install-tools ||:
rm -f $RPM_BUILD_ROOT%{_libexecdir}/gcc/%{target}/%{gcc_ver}/*.la

%global __os_install_post . ./os_install_post


%check
%if %{bootstrap}
exit 0
%endif
pushd gcc-%{target}
#BuildRequires: autoge may be needed
make check
popd

%files
%defattr(-,root,root,-)
%doc gcc-%{gcc_short_ver}-%{cs_date}/COPYING*
%doc gcc-%{gcc_short_ver}-%{cs_date}/README README.fedora
%{_bindir}/%{target}-*
%dir %{_libdir}/gcc
%dir %{_libdir}/gcc/%{target}
%{_libdir}/gcc/%{target}/%{gcc_ver}
%dir %{_libexecdir}/gcc
%dir %{_libexecdir}/gcc/%{target}
%{_libexecdir}/gcc/%{target}/%{gcc_ver}
%{_mandir}/man1/%{target}-*.1.gz
%if ! %{bootstrap}
/usr/%{target}/lib/
%exclude %{_bindir}/%{target}-?++
%exclude %{_libexecdir}/gcc/%{target}/%{gcc_ver}/cc1plus
%exclude %{_mandir}/man1/%{target}-g++.1.gz
%endif

%files c++
%defattr(-,root,root,-)
%{_bindir}/%{target}-?++
%if ! %{bootstrap}
%{_libexecdir}/gcc/%{target}/%{gcc_ver}/cc1plus
/usr/%{target}/include/c++/
%dir /usr/%{target}/share/gcc-%{gcc_ver}/python/
/usr/%{target}/share/gcc-%{gcc_ver}/python/libstdcxx/
%{_mandir}/man1/%{target}-g++.1.gz
%endif

%changelog
* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2013.11.24-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu Jan 16 2014 Michal Hlavinka <mhlavink@redhat.com> - 2013.11.24-2
- complete build with newlib

* Tue Jan 14 2014 Michal Hlavinka <mhlavink@redhat.com> - 2013.11.24-1
- updated to 2013.11-24

* Fri Oct 11 2013 Michal Hlavinka <mhlavink@redhat.com> - 2013.05.23-2
- replace arm*-g++ with explanation script that this is just unsupported 
  package used for bootstrapping

* Sun Aug 25 2013 Michal Hlavinka <mhlavink@redhat.com> - 2013.05.23-1
- updated to 2013.05-23 release (gcc 4.7.3)

* Wed Aug 14 2013 Michal Hlavinka <mhlavink@redhat.com> - 2012.09.63-3
- fix aarch64 support (#925023)

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2012.09.63-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Feb 19 2013 Michal Hlavinka <mhlavink@redhat.com> - 2012.09.63-1
- initial package

