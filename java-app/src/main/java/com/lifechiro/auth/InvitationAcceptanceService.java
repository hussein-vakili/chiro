package com.lifechiro.auth;

import com.lifechiro.auth.model.InvitationRecord;
import com.lifechiro.auth.model.PortalUserRecord;
import com.lifechiro.auth.model.SlotHoldRecord;
import com.lifechiro.shared.TimeSupport;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InvitationAcceptanceService {
    public record InvitationViewModel(
        boolean invalid,
        String invalidMessage,
        InvitationRecord invitation,
        SlotHoldRecord slotHold,
        String reservedAppointmentLabel
    ) {
    }

    public record AcceptanceResult(
        boolean success,
        String errorMessage,
        InvitationViewModel view,
        PortalUserRecord user
    ) {
    }

    private final InvitationRepository invitationRepository;
    private final SlotHoldRepository slotHoldRepository;
    private final UserRepository userRepository;
    private final AppointmentRepository appointmentRepository;
    private final LeadRepository leadRepository;
    private final PasswordEncoder passwordEncoder;

    public InvitationAcceptanceService(
        InvitationRepository invitationRepository,
        SlotHoldRepository slotHoldRepository,
        UserRepository userRepository,
        AppointmentRepository appointmentRepository,
        LeadRepository leadRepository,
        PasswordEncoder passwordEncoder
    ) {
        this.invitationRepository = invitationRepository;
        this.slotHoldRepository = slotHoldRepository;
        this.userRepository = userRepository;
        this.appointmentRepository = appointmentRepository;
        this.leadRepository = leadRepository;
        this.passwordEncoder = passwordEncoder;
    }

    public InvitationViewModel loadInvitation(String token) {
        InvitationRecord invitation = invitationRepository.findByToken(token).orElse(null);
        SlotHoldRecord slotHold = invitation == null ? null : slotHoldRepository.findByInvitationId(invitation.id()).orElse(null);
        boolean invalid = invitation == null
            || invitation.acceptedAt() != null
            || TimeSupport.isExpired(invitation.expiresAt())
            || (slotHold != null && (!slotHold.isActive() || TimeSupport.isExpired(slotHold.expiresAt())));
        String invalidMessage = invalid
            ? "The invitation may have expired, already been used, or lost its reserved appointment slot."
            : null;
        String reservedLabel = TimeSupport.formatSchedule(
            slotHold != null && slotHold.startsAt() != null ? slotHold.startsAt() : invitation != null ? invitation.appointmentAt() : null
        );
        return new InvitationViewModel(invalid, invalidMessage, invitation, slotHold, reservedLabel);
    }

    @Transactional
    public AcceptanceResult acceptInvitation(String token, String password, String confirmPassword) {
        InvitationViewModel view = loadInvitation(token);
        if (view.invalid()) {
            return new AcceptanceResult(false, view.invalidMessage(), view, null);
        }
        if (password == null || password.length() < 8) {
            return new AcceptanceResult(false, "Password must be at least 8 characters.", view, null);
        }
        if (!password.equals(confirmPassword)) {
            return new AcceptanceResult(false, "Passwords do not match.", view, null);
        }
        if (userRepository.existsByEmail(view.invitation().email())) {
            return new AcceptanceResult(false, "An account with that email already exists. Sign in instead.", view, null);
        }

        String now = TimeSupport.isoNowUtc();
        PortalUserRecord user = userRepository.createInvitedClient(
            view.invitation().firstName(),
            view.invitation().lastName(),
            view.invitation().email().toLowerCase(),
            passwordEncoder.encode(password),
            now
        );
        invitationRepository.markAccepted(view.invitation().id(), user.id(), now);
        long appointmentId = appointmentRepository.ensurePatientAppointment(user.id(), view.invitation(), view.slotHold(), now);
        if (view.slotHold() != null && appointmentId > 0) {
            slotHoldRepository.markConsumed(view.slotHold().id(), appointmentId, now);
        }
        leadRepository.markConvertedByInvitation(view.invitation().id(), user.id(), now);
        return new AcceptanceResult(true, null, loadInvitation(token), user);
    }
}
