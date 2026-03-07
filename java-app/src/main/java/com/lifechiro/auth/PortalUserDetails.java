package com.lifechiro.auth;

import com.lifechiro.auth.model.PortalUserRecord;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

public class PortalUserDetails implements UserDetails {
    private final PortalUserRecord user;
    private final List<GrantedAuthority> authorities;

    public PortalUserDetails(PortalUserRecord user) {
        this.user = user;
        this.authorities = buildAuthorities(user.role());
    }

    public PortalUserRecord user() {
        return user;
    }

    public String role() {
        return user.role();
    }

    public String displayName() {
        return user.displayName();
    }

    public boolean isClient() {
        return "client".equalsIgnoreCase(user.role());
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return authorities;
    }

    @Override
    public String getPassword() {
        return user.passwordHash();
    }

    @Override
    public String getUsername() {
        return user.email();
    }

    @Override
    public boolean isEnabled() {
        return user.active();
    }

    private static List<GrantedAuthority> buildAuthorities(String roleValue) {
        String normalized = (roleValue == null || roleValue.isBlank()) ? "client" : roleValue.toLowerCase(Locale.ROOT);
        List<GrantedAuthority> granted = new ArrayList<>();
        granted.add(new SimpleGrantedAuthority("ROLE_" + normalized.toUpperCase(Locale.ROOT)));
        if (!"client".equals(normalized)) {
            granted.add(new SimpleGrantedAuthority("ROLE_STAFF"));
        }
        return granted;
    }
}
