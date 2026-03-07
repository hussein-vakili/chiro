package com.lifechiro.dashboard;

import com.lifechiro.auth.AppointmentRepository;
import com.lifechiro.auth.InvitationRepository;
import com.lifechiro.auth.PortalUserDetails;
import com.lifechiro.auth.UserRepository;
import com.lifechiro.shared.TimeSupport;
import org.springframework.stereotype.Service;

@Service
public class DashboardService {
    private final AppointmentRepository appointmentRepository;
    private final UserRepository userRepository;
    private final InvitationRepository invitationRepository;

    public DashboardService(
        AppointmentRepository appointmentRepository,
        UserRepository userRepository,
        InvitationRepository invitationRepository
    ) {
        this.appointmentRepository = appointmentRepository;
        this.userRepository = userRepository;
        this.invitationRepository = invitationRepository;
    }

    public DashboardSummary buildSummary(PortalUserDetails principal) {
        if (principal.isClient()) {
            String nextAppointment = appointmentRepository.findNextAppointmentLabelForPatient(principal.user().id());
            return new DashboardSummary(
                "Portal home",
                nextAppointment == null
                    ? "Use your portal to manage appointments, review your care plan, and keep your next visit on track."
                    : "Your portal is linked to the live clinic diary and your next step is ready to manage here.",
                "Role",
                "Patient",
                "Next appointment",
                nextAppointment == null ? "None scheduled" : TimeSupport.formatSchedule(nextAppointment)
            );
        }
        return new DashboardSummary(
            "Staff home",
            "This Java slice currently owns authentication and invitation acceptance. Booking, care plans, and intake are the next migration targets.",
            "Clients",
            String.valueOf(userRepository.countClients()),
            "Pending invites",
            String.valueOf(invitationRepository.countPendingInvitations())
        );
    }
}
