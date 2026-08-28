.. _sanitize_api:

Sanitization objects
====================

.. currentmodule:: docx.sanitize


SanitizationReport objects
--------------------------

.. autoclass:: SanitizationReport
   :members: changed

   .. attribute:: scrubbed_properties

      Names of core properties normalized during sanitization.

   .. attribute:: removed_comment_markers

      Number of outermost comment marker elements removed from Word story XML.

   .. attribute:: removed_formatting_revisions

      Number of outermost formatting revision elements removed.

   .. attribute:: removed_parts

      Package part names made unreachable by removed relationships.

   .. attribute:: removed_relationships

      :class:`RemovedRelationship` records for relationships removed from the
      package graph.

   .. attribute:: warnings

      Non-fatal conditions encountered while sanitizing the package.


RemovedRelationship objects
---------------------------

.. autoclass:: RemovedRelationship

   .. attribute:: source

      Part name of the relationship source, or ``/`` for the package itself.

   .. attribute:: relationship_id

      Relationship identifier used by the source.

   .. attribute:: relationship_type

      Full relationship type URI.

   .. attribute:: target

      Target part name or external target reference.
